import subprocess
import time

def test_mirror_speed(mirror_url):
    """测试镜像源的响应速度"""
    try:
        start_time = time.time()
        result = subprocess.run(['curl', '-s', '-m', '5', mirror_url], 
                              capture_output=True, text=True)
        end_time = time.time()
        if result.returncode == 0:
            return end_time - start_time
        return float('inf')
    except Exception as e:
        print(f"Error testing {mirror_url}: {str(e)}")
        return float('inf')

mirrors = {
    "PyPI": "https://pypi.org/simple",
    "清华源": "https://pypi.tuna.tsinghua.edu.cn/simple",
    "阿里云": "https://mirrors.aliyun.com/pypi/simple",
    "华为云": "https://repo.huaweicloud.com/repository/pypi/simple",
    "中科大": "https://pypi.mirrors.ustc.edu.cn/simple"
}

print("测试各个镜像源的响应速度...")
results = []

for name, url in mirrors.items():
    print(f"正在测试 {name}...", end=" ")
    speed = test_mirror_speed(url)
    if speed != float('inf'):
        print(f"{speed:.3f} 秒")
        results.append((name, url, speed))
    else:
        print("连接失败")

print("\n速度排名:")
for i, (name, url, speed) in enumerate(sorted(results, key=lambda x: x[2]), 1):
    print(f"{i}. {name:<6}: {speed:.3f} 秒 ({url})")
