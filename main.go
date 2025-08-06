package main

import (
	"errors"
	"fmt"
	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"
)

// 查询请求参数
type QueryRequest struct {
	Name string `json:"name" binding:"required"`
	ID   string `json:"id" binding:"required"`
}

// 令牌结构
type DownloadToken struct {
	Token    string
	FilePath string
	Expire   time.Time
}

// 查询响应
type QueryResponse struct {
	Message string `json:"message"`
	FileURL string `json:"file_url,omitempty"`
	Token   string `json:"token,omitempty"`
}

var (
	tokenStore   = &sync.Map{}
	tokenMutex   = &sync.Mutex{}
	fileCache    = &sync.Map{} // 文件查找缓存
	cacheMutex   = &sync.Mutex{}
	cleanupTicker *time.Ticker // 定时清理器
)

// IP访问记录
type accessRecord struct {
	timestamps []time.Time
	mu         sync.Mutex
}

var ipRecords = &sync.Map{}

func main() {
	// 启动定时清理任务
	startCleanupTask()
	defer cleanupTicker.Stop()

	r := gin.Default()

	// 静态文件服务
	r.Static("/assets", "./assets")

	// 加载模板
	r.LoadHTMLGlob("templates/*")

	// 路由配置
	r.GET("/", func(c *gin.Context) {
		c.HTML(http.StatusOK, "index.html", nil)
	})

	r.POST("/query", func(c *gin.Context) {
		// 1. 绑定请求参数
		var req QueryRequest
		if err := c.ShouldBindJSON(&req); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "无效的请求参数"})
			return
		}

		// 2. 频率限制检查
		if err := checkRateLimit(c.ClientIP()); err != nil {
			c.JSON(http.StatusTooManyRequests, gin.H{"error": err.Error()})
			return
		}

		// 3. 查找准考证文件
		filePath, err := findAdmitCard(req.ID, req.Name)
		if err != nil {
			c.JSON(http.StatusOK, QueryResponse{
				Message: fmt.Sprintf("未找到%s的准考证，请检查信息是否匹配。", req.Name),
			})
			return
		}

		// 4. 生成下载令牌
		token := generateToken(filePath)
		
		// 5. 返回成功响应
		c.JSON(http.StatusOK, QueryResponse{
			Message: fmt.Sprintf("查询到%s的准考证，已自动开始下载。", req.Name),
			FileURL: fmt.Sprintf("/download?path=%s&token=%s", url.QueryEscape(filePath), token),
			Token:   token,
		})
	})
	
	// 文件下载路由
	r.GET("/download", func(c *gin.Context) {
		filePath := c.Query("path")
		token := c.Query("token")
		
		if filePath == "" {
			c.JSON(http.StatusBadRequest, gin.H{"error": "缺少文件路径参数"})
			return
		}
		
		// 验证令牌
		if !validateToken(token, filePath) {
			c.JSON(http.StatusForbidden, gin.H{"error": "无效或过期的下载令牌"})
			return
		}
		
		// 安全检查：确保文件在AdmitCards目录下
		if !strings.HasPrefix(filepath.Clean(filePath), "AdmitCards"+string(filepath.Separator)) {
			c.JSON(http.StatusForbidden, gin.H{"error": "非法文件路径"})
			return
		}
		
		// 设置动态下载文件名（兼容Firefox）
		_, fileName := filepath.Split(filePath)
		c.Header("Content-Disposition", `attachment; filename*=UTF-8''`+url.PathEscape(fileName))
		c.Header("Content-Type", "application/pdf")
		c.Header("X-Content-Type-Options", "nosniff")
		c.File(filePath)
	})

	// 启动服务器
	r.Run(":8080")
}

// 标准化姓名（处理少数民族姓名中的·）
func normalizeName(name string) string {
	if idx := strings.Index(name, "·"); idx != -1 {
		return name[:idx] // 取·前部分
	}
	return name
}

// 查找准考证文件
func findAdmitCard(id, name string) (string, error) {
	// 生成缓存键
	cacheKey := fmt.Sprintf("%s-%s", id, normalizeName(name))
	
	// 检查缓存
	if val, ok := fileCache.Load(cacheKey); ok {
		if filePath, ok := val.(string); ok {
			return filePath, nil
		}
	}
	
	// 查找文件
	targetFile := fmt.Sprintf("%s-%s.pdf", id, normalizeName(name))
	filePath := filepath.Join("AdmitCards", targetFile)
	if _, err := os.Stat(filePath); err == nil {
		// 存入缓存(5分钟有效期)
		fileCache.Store(cacheKey, filePath)
		time.AfterFunc(5*time.Minute, func() {
			fileCache.Delete(cacheKey)
		})
		return filePath, nil
	}
	return "", errors.New("file not found")
}

// 启动定时清理任务
func startCleanupTask() {
	cleanupTicker = time.NewTicker(30 * time.Minute)
	go func() {
		for range cleanupTicker.C {
			// 清理过期令牌
			tokenStore.Range(func(key, value interface{}) bool {
				token := value.(DownloadToken)
				if time.Now().After(token.Expire) {
					tokenStore.Delete(key)
				}
				return true
			})
		}
	}()
}

// 检查频率限制
func checkRateLimit(ip string) error {
	record, _ := ipRecords.LoadOrStore(ip, &accessRecord{})
	ar := record.(*accessRecord)

	ar.mu.Lock()
	defer ar.mu.Unlock()

	now := time.Now()
	
	// 清理过期记录
	ar.timestamps = cleanExpiredRecords(ar.timestamps, now)

	// 检查限制
	if err := checkLimits(ar.timestamps, now); err != nil {
		return err
	}

	// 添加新记录
	ar.timestamps = append(ar.timestamps, now)
	return nil
}

// 生成下载令牌
func generateToken(filePath string) string {
	token := uuid.New().String()
	expire := time.Now().Add(5 * time.Minute)
	
	tokenMutex.Lock()
	defer tokenMutex.Unlock()
	
	tokenStore.Store(token, DownloadToken{
		Token:    token,
		FilePath: filePath,
		Expire:   expire,
	})
	
	return token
}

// 验证下载令牌
func validateToken(token, filePath string) bool {
	if token == "" {
		fmt.Printf("验证失败: 空令牌 (请求文件: %s)\n", filePath)
		return false
	}
	
	tokenMutex.Lock()
	defer tokenMutex.Unlock()
	
	// 获取令牌
	val, ok := tokenStore.Load(token)
	if !ok {
		// 打印当前存储的所有令牌用于调试
		var storedTokens []string
		tokenStore.Range(func(key, value interface{}) bool {
			storedTokens = append(storedTokens, key.(string))
			return true
		})
		fmt.Printf("验证失败: 令牌不存在 %s (存储的令牌: %v, 请求文件: %s)\n", token, storedTokens, filePath)
		return false
	}
	
	dt := val.(DownloadToken)
	
	// 检查令牌是否过期
	if time.Now().After(dt.Expire) {
		fmt.Printf("验证失败: 令牌过期 %s (过期时间: %v)\n", token, dt.Expire)
		tokenStore.Delete(token)
		return false
	}
	
	// 检查文件路径是否匹配
	if dt.FilePath != filePath {
		fmt.Printf("验证失败: 文件路径不匹配 (令牌路径: %s, 请求路径: %s)\n", dt.FilePath, filePath)
		return false
	}
	
	// 验证通过后删除令牌(一次性使用)
	tokenStore.Delete(token)
	fmt.Printf("验证成功: 令牌 %s 用于文件 %s\n", token, filePath)
	return true
}

// 清理过期记录
func cleanExpiredRecords(records []time.Time, now time.Time) []time.Time {
	var valid []time.Time
	for _, t := range records {
		if now.Sub(t) < 24*time.Hour { // 保留24小时内的记录
			valid = append(valid, t)
		}
	}
	return valid
}

// 检查各种限制
func checkLimits(records []time.Time, now time.Time) error {
	var (
		minuteCount int
		hourCount   int
		dayCount    = len(records)
	)

	for _, t := range records {
		if now.Sub(t) < time.Minute {
			minuteCount++
		}
		if now.Sub(t) < time.Hour {
			hourCount++
		}
	}

	if minuteCount >= 5 {
		nextMinute := time.Unix(now.Unix()/60*60+60, 0)
		return errors.New("操作频繁，请" + nextMinute.Sub(now).Round(time.Second).String() + "后重试")
	}
	if hourCount >= 60 {
		nextHour := time.Unix(now.Unix()/3600*3600+3600, 0)
		return errors.New("操作频繁，请" + nextHour.Sub(now).Round(time.Second).String() + "后重试")
	}
	if dayCount >= 300 {
		nextDay := time.Unix(now.Unix()/86400*86400+86400, 0)
		return errors.New("操作频繁，请" + nextDay.Sub(now).Round(time.Second).String() + "后重试")
	}

	return nil
}
