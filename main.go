package main

import (
	"github.com/gin-gonic/gin"
	"net/http"
	"path/filepath"
	"strings"
)

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

	r.POST("/query", queryHandler)
	
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
