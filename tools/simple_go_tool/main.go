package main

import (
	"encoding/json"
	"fmt"
	"io/ioutil"
	"os"
	"path/filepath"
	"strings"
	"time"
)

type Result struct {
	Success   bool                   `json:"success"`
	Tool      string                 `json:"tool"`
	Analysis  map[string]interface{} `json:"analysis,omitempty"`
	Error     string                 `json:"error,omitempty"`
	Timestamp string                 `json:"timestamp"`
}

func analyzeFile(inputFile string) Result {
	// Read file
	content, err := ioutil.ReadFile(inputFile)
	if err != nil {
		return Result{
			Success:   false,
			Error:     fmt.Sprintf("Failed to read file: %v", err),
			Timestamp: time.Now().UTC().Format(time.RFC3339),
		}
	}

	text := string(content)
	lines := strings.Split(text, "\n")
	words := strings.Fields(text)

	// Simple Go-style analysis
	analysis := map[string]interface{}{
		"file_size_bytes":     len(content),
		"lines":              len(lines),
		"words":              len(words),
		"characters":         len(text),
		"non_empty_lines":    countNonEmptyLines(lines),
		"uppercase_words":    countUppercaseWords(words),
		"go_keywords":        countGoKeywords(words),
		"processed_by":       "go_analyzer",
	}

	// Save report
	reportsDir := "/shared/reports"
	os.MkdirAll(reportsDir, 0755)
	
	timestamp := time.Now().Format("20060102_150405")
	reportPath := filepath.Join(reportsDir, fmt.Sprintf("go_analysis_%s.json", timestamp))
	
	result := Result{
		Success:   true,
		Tool:      "go_analyzer",
		Analysis:  analysis,
		Timestamp: time.Now().UTC().Format(time.RFC3339),
	}
	
	reportData, _ := json.MarshalIndent(result, "", "  ")
	ioutil.WriteFile(reportPath, reportData, 0644)
	
	fmt.Printf("Report saved to: %s\n", reportPath)
	return result
}

func countNonEmptyLines(lines []string) int {
	count := 0
	for _, line := range lines {
		if strings.TrimSpace(line) != "" {
			count++
		}
	}
	return count
}

func countUppercaseWords(words []string) int {
	count := 0
	for _, word := range words {
		if word == strings.ToUpper(word) && len(word) > 1 {
			count++
		}
	}
	return count
}

func countGoKeywords(words []string) int {
	keywords := map[string]bool{
		"func": true, "var": true, "const": true, "type": true,
		"package": true, "import": true, "if": true, "else": true,
		"for": true, "range": true, "return": true, "go": true,
	}
	
	count := 0
	for _, word := range words {
		if keywords[strings.ToLower(word)] {
			count++
		}
	}
	return count
}

func main() {
	if len(os.Args) != 2 {
		fmt.Println("Usage: go_analyzer <input_file>")
		os.Exit(1)
	}

	inputFile := os.Args[1]
	result := analyzeFile(inputFile)

	// Print result as JSON
	jsonData, _ := json.MarshalIndent(result, "", "  ")
	fmt.Println(string(jsonData))

	if !result.Success {
		os.Exit(1)
	}
}