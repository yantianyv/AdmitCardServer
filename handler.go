package main

import (
	"errors"
	"fmt"
	"github.com/gin-gonic/gin"
	"net/http"
	"os"
	"path/filepath"
	"strings"
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

func queryHandler(c *gin.Context) {
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
