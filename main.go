package main

import (
	"bytes"
	"fmt"
	"os"
	"strings"
	"unicode/utf16"

	"github.com/out-lang/out/internal/env"
	"github.com/out-lang/out/internal/eval"
	"github.com/out-lang/out/internal/lexer"
	"github.com/out-lang/out/internal/libs"
	"github.com/out-lang/out/internal/object"
	"github.com/out-lang/out/internal/parser"
)

const VERSION = "v0.5.0"

const outEmbedMarker = "\n__OUT_EMBED_START__\n"
const outEmbedEndMarker = "\n__OUT_EMBED_END__\n"

func main() {
	if len(os.Args) > 1 {
		switch os.Args[1] {
		case "--version", "-v":
			fmt.Println("OUT " + VERSION)
			os.Exit(0)
		case "--help", "-h":
			printHelp()
			os.Exit(0)
		case "run":
			if len(os.Args) < 3 {
				fmt.Println("Usage: out run <filename.out>")
				os.Exit(1)
			}
			runFile(os.Args[2])
		case "compile":
			if len(os.Args) < 3 {
				fmt.Println("Usage: out compile <file.out> [output.exe]")
				os.Exit(1)
			}
			compileFile(os.Args[2], outArg(os.Args, 3))
		case "get":
			if len(os.Args) < 3 {
				fmt.Println("Usage: out get <library>")
				fmt.Println("  out get random")
				fmt.Println("  out get user/repo/lib")
				fmt.Println("  out get https://example.com/lib.out")
				os.Exit(1)
			}
			if err := libs.Get(os.Args[2]); err != nil {
				fmt.Fprintf(os.Stderr, "Error: %s\n", err)
				os.Exit(1)
			}
		case "libs":
			libs.List()
		case "errors":
			if len(os.Args) < 3 {
				fmt.Println("Usage: out errors <file.out>")
				os.Exit(1)
			}
			showErrors(os.Args[2])
		default:
			runFile(os.Args[1])
		}
	} else {
		if script, ok := embeddedScript(); ok {
			runSource(script, "embedded")
		} else {
			runRepl()
		}
	}
}

func outArg(args []string, i int) string {
	if len(args) > i {
		return args[i]
	}
	return ""
}

func embeddedScript() (string, bool) {
	self, err := os.Executable()
	if err != nil {
		return "", false
	}
	data, err := os.ReadFile(self)
	if err != nil {
		return "", false
	}
	marker := []byte(outEmbedMarker)
	firstIdx := bytes.Index(data, marker)
	if firstIdx < 0 {
		return "", false
	}
	secondIdx := bytes.Index(data[firstIdx+len(marker):], marker)
	if secondIdx < 0 {
		return "", false
	}
	start := firstIdx + len(marker) + secondIdx + len(marker)
	endMarker := []byte(outEmbedEndMarker)
	endIdx := bytes.Index(data[start:], endMarker)
	if endIdx < 0 {
		return "", false
	}
	script := data[start : start+endIdx]
	if len(script) == 0 {
		return "", false
	}
	return string(script), true
}

func compileFile(filename, output string) {
	if output == "" {
		output = stripExt(filename) + ".exe"
	}
	script, err := os.ReadFile(filename)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error reading file: %s\n", err)
		os.Exit(1)
	}

	l := lexer.New(string(script))
	p := parser.New(l)
	p.ParseProgram()
	if len(p.Errors()) != 0 {
		fmt.Fprintf(os.Stderr, "Compilation failed: %d error(s)\n\n", len(p.Errors()))
		for i, msg := range p.Errors() {
			fmt.Fprintf(os.Stderr, "  %d) %s\n", i+1, msg)
		}
		fmt.Fprintf(os.Stderr, "\nFile: %s\n", filename)
		os.Exit(1)
	}

	self, err := os.Executable()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: %s\n", err)
		os.Exit(1)
	}
	engine, err := os.ReadFile(self)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error reading engine: %s\n", err)
		os.Exit(1)
	}

	var buf bytes.Buffer
	buf.Write(engine)
	buf.WriteString(outEmbedMarker)
	buf.Write(script)
	buf.WriteString(outEmbedEndMarker)

	if err := os.WriteFile(output, buf.Bytes(), 0755); err != nil {
		fmt.Fprintf(os.Stderr, "Error writing: %s\n", err)
		os.Exit(1)
	}
	fmt.Printf("compiled: %s\n", output)
}

func stripExt(name string) string {
	for i := len(name) - 1; i >= 0; i-- {
		if name[i] == '.' {
			return name[:i]
		}
	}
	return name
}

func showErrors(filename string) {
	data, err := os.ReadFile(filename)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: %s\n", err)
		os.Exit(1)
	}

	l := lexer.New(string(data))
	p := parser.New(l)
	p.ParseProgram()

	if len(p.Errors()) == 0 {
		fmt.Println("No errors found.")
		return
	}

	var sb strings.Builder
	sb.WriteString(fmt.Sprintf("File: %s\n", filename))
	sb.WriteString(fmt.Sprintf("Errors: %d\n\n", len(p.Errors())))

	for i, msg := range p.Errors() {
		sb.WriteString(fmt.Sprintf("%d) %s\n", i+1, msg))
	}

	fmt.Print(sb.String())

	clipboard := sb.String()
	if err := os.WriteFile("last_error.txt", []byte(clipboard), 0644); err == nil {
		fmt.Println("\n[Saved to last_error.txt]")
	}
}

func runFile(filename string) {
	data, err := os.ReadFile(filename)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error reading file: %s\n", err)
		os.Exit(1)
	}
	src := decodeUTF16(data)
	runSource(src, filename)
}

func decodeUTF16(data []byte) string {
	if len(data) >= 3 && data[0] == 0xEF && data[1] == 0xBB && data[2] == 0xBF {
		data = data[3:]
	}
	if len(data) < 2 {
		return string(data)
	}
	if data[0] == 0xFF && data[1] == 0xFE {
		u16 := make([]uint16, (len(data)-2)/2)
		for i := range u16 {
			u16[i] = uint16(data[2+i*2]) | uint16(data[3+i*2])<<8
		}
		return string(utf16.Decode(u16))
	}
	if data[0] == 0xFE && data[1] == 0xFF {
		u16 := make([]uint16, (len(data)-2)/2)
		for i := range u16 {
			u16[i] = uint16(data[2+i*2])<<8 | uint16(data[3+i*2])
		}
		return string(utf16.Decode(u16))
	}
	if len(data) >= 2 && data[1] == 0x00 {
		u16 := make([]uint16, len(data)/2)
		for i := range u16 {
			u16[i] = uint16(data[i*2]) | uint16(data[i*2+1])<<8
		}
		return string(utf16.Decode(u16))
	}
	return string(data)
}

func runSource(src, name string) {
	l := lexer.New(src)
	p := parser.New(l)
	program := p.ParseProgram()

	if len(p.Errors()) != 0 {
		for _, msg := range p.Errors() {
			fmt.Fprintf(os.Stderr, "Parse error: %s\n", msg)
		}
		os.Exit(1)
	}

	e := env.New()
	result := eval.Eval(program, e)

	if result != nil {
		if errObj, ok := result.(*object.Error); ok {
			fmt.Fprintf(os.Stderr, "Runtime error: %s\n", errObj.Message)
			os.Exit(1)
		}
	}
}

func printHelp() {
	const help = `
OUT Language ` + VERSION + `

Usage:
  out                        Start REPL
  out run <file.out>        Run a file
  out <file.out>            Run a file (shorthand)
  out compile <file> [o]    Compile to standalone .exe
  out errors <file.out>     Show compilation errors (copyable)
  out get <library>         Download library from GitHub
  out libs                  List installed libraries
  out --version             Show version
  out --help                Show this help

Examples:
  out run hello.out
  out compile hello.out  ->  hello.exe
  out errors script.out  ->  shows errors + saves to last_error.txt
  out get random`
	fmt.Println(help)
}

func runRepl() {
	fmt.Println("OUT Language " + VERSION)
	fmt.Println("Type 'exit' or Ctrl+D to quit")
	fmt.Println()

	e := env.New()

	for {
		fmt.Print(">> ")
		var input string
		n, err := fmt.Scanln(&input)
		if n == 0 || err != nil {
			fmt.Println()
			break
		}
		if input == "exit" || input == "quit" {
			break
		}

		l := lexer.New(input)
		p := parser.New(l)
		program := p.ParseProgram()

		if len(p.Errors()) != 0 {
			for _, msg := range p.Errors() {
				fmt.Printf("  %s\n", msg)
			}
			continue
		}

		result := eval.Eval(program, e)
		if result != nil {
			resultStr := result.Inspect()
			if resultStr != "" {
				fmt.Printf("= %s\n", resultStr)
			}
		}
	}
}