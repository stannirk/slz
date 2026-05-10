import random
import time

users = ["root", "user", "daemon", "db_admin", "app_srv"]
procs = ["python", "node", "chrome", "docker-proxy", "nginx", "postgres", "redis-server", "zsh", "slz"]

print(f"{'USER':<10} {'PID':<8} {'%CPU':<5} {'%MEM':<5} {'COMMAND'}")
for i in range(1, 150):
    user = random.choice(users)
    pid = 1000 + i
    cpu = round(random.uniform(0, 10), 1)
    mem = round(random.uniform(0, 15), 1)
    cmd = random.choice(procs)
    if cmd == "python":
        cmd += f" src/slz/__init__.py"
    elif cmd == "chrome":
        cmd += f" --type=renderer --no-sandbox"
    
    print(f"{user:<10} {pid:<8} {cpu:<5} {mem:<5} {cmd}")
