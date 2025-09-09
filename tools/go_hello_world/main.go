package main

import (
	"encoding/json"
	"fmt"
	"os"
	"runtime"
	"strings"
	"time"
)

// Hello World tool written in Go for Dagger execution
// Demonstrates multi-language tool support in Praxis

func main() {
	fmt.Println("🔄 GO HELLO WORLD TOOL STARTED")
	fmt.Println("=" * 50)

	// Get parameters from environment variables (passed through Dagger)
	name := getEnv("ARG_NAME", "World")
	message := getEnv("ARG_MESSAGE", "Hello from Go!")
	format := strings.ToLower(getEnv("ARG_FORMAT", "text"))

	fmt.Printf("🎯 Input Parameters:\n")
	fmt.Printf("   👤 Name: %s\n", name)
	fmt.Printf("   💬 Message: %s\n", message) 
	fmt.Printf("   📊 Format: %s\n", format)
	fmt.Println("-" * 50)

	// Simulate some processing
	fmt.Println("⏳ Processing request...")
	time.Sleep(1 * time.Second)

	// Get system information
	sysInfo := map[string]interface{}{
		"go_version":    runtime.Version(),
		"goos":          runtime.GOOS,
		"goarch":        runtime.GOARCH,
		"goroutines":    runtime.NumGoroutine(),
		"cpu_count":     runtime.NumCPU(),
		"tool_name":     "go_hello_world",
		"execution_time": time.Now().Format(time.RFC3339),
	}

	// Create result
	result := map[string]interface{}{
		"greeting":    fmt.Sprintf("%s, %s!", message, name),
		"language":    "Go",
		"system_info": sysInfo,
		"success":     true,
		"timestamp":   time.Now().Unix(),
	}

	// Output result based on format
	if format == "json" {
		jsonOutput, err := json.MarshalIndent(result, "", "  ")
		if err != nil {
			fmt.Printf("❌ Error marshaling JSON: %v\n", err)
			os.Exit(1)
		}
		fmt.Println("📋 JSON OUTPUT:")
		fmt.Println(string(jsonOutput))
	} else {
		fmt.Println("📋 EXECUTION RESULTS:")
		fmt.Printf("✨ Greeting: %s\n", result["greeting"])
		fmt.Printf("🔤 Language: %s\n", result["language"]) 
		fmt.Printf("🖥️  Go Version: %s\n", sysInfo["go_version"])
		fmt.Printf("💻 Platform: %s/%s\n", sysInfo["goos"], sysInfo["goarch"])
		fmt.Printf("🧮 CPUs: %d\n", sysInfo["cpu_count"])
		fmt.Printf("⏰ Execution Time: %s\n", sysInfo["execution_time"])
	}

	fmt.Println("-" * 50)
	fmt.Println("✅ GO TOOL EXECUTION COMPLETED")
}

func getEnv(key, defaultValue string) string {
	if value, exists := os.LookupEnv(key); exists {
		return value
	}
	return defaultValue
}