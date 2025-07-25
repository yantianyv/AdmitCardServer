package main

import (
	"errors"
	"fmt"
	"github.com/gin-gonic/gin"
	"net/http"
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

// 查询响应
type QueryResponse struct {
	Message string `json:"message"`
	FileURL string `json:"file_url,omitempty"`
}

// IP访问记录
type accessRecord struct {
	timestamps []time.Time
	mu         sync.Mutex
}

var ipRecords = &sync.Map{}

func main() {
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

		// 4. 返回成功响应
		c.JSON(http.StatusOK, QueryResponse{
			Message: fmt.Sprintf("查询到%s的准考证，已自动开始下载。", req.Name),
			FileURL: "/download?path=" + filePath,
		})
	})
	
	// 文件下载路由
	r.GET("/download", func(c *gin.Context) {
		filePath := c.Query("path")
		if filePath == "" {
			c.JSON(http.StatusBadRequest, gin.H{"error": "缺少文件路径参数"})
			return
		}
		
		// 安全检查：确保文件在AdmitCards目录下
		if !strings.HasPrefix(filepath.Clean(filePath), "AdmitCards"+string(filepath.Separator)) {
			c.JSON(http.StatusForbidden, gin.H{"error": "非法文件路径"})
			return
		}
		
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
	normalizedName := normalizeName(name)
	targetFile := fmt.Sprintf("%s-%s.pdf", id, normalizedName)
	
	filePath := filepath.Join("AdmitCards", targetFile)
	if _, err := os.Stat(filePath); err == nil {
		return filePath, nil
	}
	return "", errors.New("file not found")
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
