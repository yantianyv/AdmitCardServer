package main

import (
	"errors"
	"sync"
	"time"
)

// IP访问记录
type accessRecord struct {
	timestamps []time.Time
	mu         sync.Mutex
}

var ipRecords = &sync.Map{}

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
