import subprocess

process = subprocess.Popen(
    ["ollama", "run", "deepseek-r1:1.5b", "Say hello"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

for line in process.stdout:
    print(line, end="")

process.wait()
