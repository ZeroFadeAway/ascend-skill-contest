#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Qwen3-06B vLLM部署脚本（Python版本）
用于在昇腾NPU上部署Qwen3-06B模型并验证
"""

import os
import sys
import time
import subprocess
import json
import paramiko
import io
import getpass

# 颜色定义
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color

# 日志文件
LOG_FILE = "deployment.log"

# 初始化日志
def log(level, message):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    
    color = Colors.BLUE if level == "INFO" else \
            Colors.GREEN if level == "SUCCESS" else \
            Colors.YELLOW if level == "WARNING" else \
            Colors.RED if level == "ERROR" else ""
    
    log_message = f"{timestamp} - [{level}] {message}"
    
    # 打印到控制台（带颜色）
    print(f"{color}{log_message}{Colors.NC}")
    
    # 写入日志文件（无颜色）
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{log_message}\n")

# 主函数
def main():
    import argparse
    
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description='Qwen3-0.6B vLLM部署脚本')
    
    # 添加命令行参数
    parser.add_argument('--host', type=str, help='服务器IP地址')
    parser.add_argument('--user', type=str, help='SSH用户名')
    parser.add_argument('--password', type=str, help='SSH密码')
    parser.add_argument('--model-path', type=str, default='/home/zxq/weight/Qwen3-06B', help='模型权重路径（默认: /home/zxq/weight/Qwen3-06B）')
    parser.add_argument('--port', type=int, default=8000, help='服务端口（默认: 8000）')
    parser.add_argument('--container-name', type=str, default='qwen3-06b-vllm', help='容器名称（默认: qwen3-06b-vllm）')
    
    # 解析命令行参数
    args = parser.parse_args()
    
    log("INFO", "========================================")
    log("INFO", "Qwen3-0.6B vLLM部署脚本")
    log("INFO", "========================================")
    
    # 获取服务器IP
    if args.host:
        server_ip = args.host
    else:
        server_ip = input("服务器IP地址: ").strip()
        if not server_ip:
            log("ERROR", "服务器IP地址不能为空")
            sys.exit(1)
    
    # 获取SSH用户名
    if args.user:
        ssh_user = args.user
    else:
        ssh_user = input("SSH用户名: ").strip()
        if not ssh_user:
            log("ERROR", "SSH用户名不能为空")
            sys.exit(1)
    
    # 获取SSH密码
    if args.password:
        ssh_password = args.password
    else:
        ssh_password = getpass.getpass("SSH密码: ").strip()
        if not ssh_password:
            log("ERROR", "SSH密码不能为空")
            sys.exit(1)
    
    # 获取模型路径
    model_path = args.model_path
    
    # 获取服务端口
    port = args.port
    
    # 获取容器名称
    container_name = args.container_name
    
    log("SUCCESS", "参数输入完成")
    log("INFO", f"服务器IP: {server_ip}")
    log("INFO", f"SSH用户名: {ssh_user}")
    log("INFO", f"模型路径: {model_path}")
    log("INFO", f"服务端口: {port}")
    log("INFO", f"容器名称: {container_name}")
    
    # 2. 创建远程部署脚本
    log("INFO", "创建远程部署脚本...")
    
    remote_script = '''
#!/bin/bash

# 远程部署脚本
LOG_FILE="remote_deployment.log"

log() {
    local level="$1"
    local message="$2"
    local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    echo "${timestamp} - [${level}] ${message}" >> $LOG_FILE
}

# 解析参数
MODEL_PATH="{0}"
PORT="{1}"
CONTAINER_NAME="{2}"
IMAGE="quay.io/ascend/vllm-ascend:v0.17.0rc1"

log "INFO" "开始远程部署"
log "INFO" "模型路径: $MODEL_PATH"
log "INFO" "服务端口: $PORT"
log "INFO" "容器名称: $CONTAINER_NAME"

# 检查Docker
log "INFO" "检查Docker环境..."
if ! command -v docker &> /dev/null; then
    log "INFO" "Docker未安装，尝试安装..."
    apt-get update &>> $LOG_FILE
    apt-get install -y docker.io &>> $LOG_FILE
    if command -v docker &> /dev/null; then
        log "SUCCESS" "Docker安装成功"
        systemctl start docker &>> $LOG_FILE
        systemctl enable docker &>> $LOG_FILE
    else
        log "ERROR" "Docker安装失败"
        echo "Docker安装失败" > /tmp/deploy_result.txt
        exit 1
    fi
else
    log "INFO" "Docker已安装"
    if ! systemctl is-active docker &> /dev/null; then
        log "INFO" "Docker服务未运行，尝试启动..."
        systemctl start docker &>> $LOG_FILE
        if systemctl is-active docker &> /dev/null; then
            log "SUCCESS" "Docker服务启动成功"
        else
            log "ERROR" "Docker服务启动失败"
            echo "Docker服务启动失败" > /tmp/deploy_result.txt
            exit 1
        fi
    else
        log "SUCCESS" "Docker服务正在运行"
    fi
fi

# 检查模型路径
log "INFO" "检查模型路径..."
if [ ! -d "$MODEL_PATH" ]; then
    log "ERROR" "模型路径不存在: $MODEL_PATH"
    echo "模型路径不存在: $MODEL_PATH" > /tmp/deploy_result.txt
    exit 1
else
    log "SUCCESS" "模型路径存在"
fi

# 拉取镜像
log "INFO" "拉取vLLM镜像..."
if ! docker images -q $IMAGE &> /dev/null; then
    docker pull $IMAGE &>> $LOG_FILE
    if [ $? -eq 0 ]; then
        log "SUCCESS" "镜像拉取成功"
    else
        log "ERROR" "镜像拉取失败"
        echo "镜像拉取失败" > /tmp/deploy_result.txt
        exit 1
    fi
else
    log "SUCCESS" "镜像已存在，跳过拉取"
fi

# 清理旧容器
log "INFO" "清理旧容器..."
docker rm -f $CONTAINER_NAME 2>/dev/null || true
log "SUCCESS" "旧容器清理完成"

# 启动新容器
log "INFO" "启动vLLM容器..."
docker run -d --name $CONTAINER_NAME \
    --shm-size=1g \
    --net=host \
    --device /dev/davinci0 \
    --device /dev/davinci_manager \
    --device /dev/devmm_svm \
    --device /dev/hisi_hdc \
    -v /usr/local/dcmi:/usr/local/dcmi \
    -v /usr/local/Ascend/driver/tools/hccn_tool:/usr/local/Ascend/driver/tools/hccn_tool \
    -v /usr/local/bin/npu-smi:/usr/local/bin/npu-smi \
    -v /usr/local/Ascend/driver/lib64/:/usr/local/Ascend/driver/lib64/ \
    -v /usr/local/Ascend/driver/version.info:/usr/local/Ascend/driver/version.info \
    -v /etc/ascend_install.info:/etc/ascend_install.info \
    -v /root/.cache:/root/.cache \
    -v $MODEL_PATH:$MODEL_PATH \
    $IMAGE bash -c "export ASCEND_RT_VISIBLE_DEVICES=0; source /usr/local/Ascend/ascend-toolkit/set_env.sh; python -m vllm.entrypoints.openai.api_server --model $MODEL_PATH --host 0.0.0.0 --port $PORT --trust-remote-code --max-model-len 4096 --tensor-parallel-size 1" &>> $LOG_FILE

if [ $? -eq 0 ]; then
    log "SUCCESS" "容器启动成功"
else
    log "ERROR" "容器启动失败"
    docker logs $CONTAINER_NAME >> $LOG_FILE
    echo "容器启动失败" > /tmp/deploy_result.txt
    exit 1
fi

# 等待服务启动
log "INFO" "等待服务启动..."
MAX_WAIT=300
WAIT_COUNT=0
SERVICE_READY=false

while [ $WAIT_COUNT -lt $MAX_WAIT ]; do
    if netstat -tlnp | grep :$PORT &> /dev/null || lsof -i:$PORT &> /dev/null; then
        log "SUCCESS" "服务已在端口 $PORT 监听"
        SERVICE_READY=true
        break
    fi
    
    # 检查容器状态
    if ! docker inspect -f '{{.State.Running}}' $CONTAINER_NAME 2>/dev/null | grep -q "true"; then
        log "ERROR" "容器已停止，查看日志..."
        docker logs $CONTAINER_NAME >> $LOG_FILE
        echo "容器已停止" > /tmp/deploy_result.txt
        exit 1
    fi
    
    log "INFO" "等待中... ($WAIT_COUNT/$MAX_WAIT秒)"
    sleep 5
    WAIT_COUNT=$((WAIT_COUNT+5))
done

if [ $SERVICE_READY = false ]; then
    log "ERROR" "服务启动超时"
    echo "服务启动超时" > /tmp/deploy_result.txt
    exit 1
fi

# 测试推理功能 - 发送"你好"
log "INFO" "测试推理功能 - 发送'你好'..."

# 记录开始时间
START_TIME=$(date +%s.%N)

# 发送测试请求
RESPONSE=$(curl -s -X POST http://localhost:$PORT/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d '{"model": "qwen3-06b", "messages": [{"role": "user", "content": "你好"}], "temperature": 0.7, "max_tokens": 100}')

# 记录结束时间
END_TIME=$(date +%s.%N)
RESPONSE_TIME=$(echo "$END_TIME - $START_TIME" | bc)

if echo "$RESPONSE" | grep -q "choices"; then
    log "SUCCESS" "推理测试成功"
    log "INFO" "响应时间: $RESPONSE_TIME 秒"
    
    # 保存测试结果
    echo "SUCCESS" > /tmp/deploy_result.txt
    echo "$RESPONSE_TIME" > /tmp/response_time.txt
    echo "$RESPONSE" > /tmp/test_response.txt
else
    log "ERROR" "推理测试失败"
    log "INFO" "响应内容: $RESPONSE"
    echo "FAILED" > /tmp/deploy_result.txt
    echo "0" > /tmp/response_time.txt
    echo "$RESPONSE" > /tmp/test_response.txt
    exit 1
fi

log "SUCCESS" "部署完成！"
'''.format(model_path, port, container_name)
    
    log("SUCCESS", "远程部署脚本创建完成")
    
    # 3. 连接到服务器并执行部署
    log("INFO", "连接到服务器...")
    
    try:
        # 创建SSH客户端
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(server_ip, 22, ssh_user, ssh_password, timeout=30)
        
        log("SUCCESS", f"成功连接到服务器: {server_ip}")
        
        # 创建SFTP客户端上传脚本
        sftp = ssh.open_sftp()
        script_bytes = remote_script.encode('utf-8')
        sftp.putfo(io.BytesIO(script_bytes), "/tmp/vllm_deploy_remote.sh")
        sftp.close()
        
        log("SUCCESS", "脚本上传成功")
        
        # 添加执行权限
        ssh.exec_command("chmod +x /tmp/vllm_deploy_remote.sh")
        
        # 执行远程部署脚本
        log("INFO", "执行远程部署...")
        log("INFO", "这可能需要几分钟时间，请耐心等待...")
        
        stdin, stdout, stderr = ssh.exec_command("bash /tmp/vllm_deploy_remote.sh", timeout=600)
        
        # 获取执行结果
        exit_code = stdout.channel.recv_exit_status()
        
        if exit_code == 0:
            log("SUCCESS", "远程部署脚本执行完成")
        else:
            log("ERROR", "远程部署脚本执行失败")
            # 获取远程日志
            try:
                sftp = ssh.open_sftp()
                sftp.get("/tmp/remote_deployment.log", "./remote_deployment.log")
                sftp.close()
                log("INFO", "远程日志已下载到: ./remote_deployment.log")
            except Exception as e:
                log("WARNING", f"下载远程日志失败: {str(e)}")
            sys.exit(1)
        
        # 4. 获取测试结果
        log("INFO", "获取测试结果...")
        
        # 下载结果文件
        sftp = ssh.open_sftp()
        
        # 下载部署结果
        with sftp.open("/tmp/deploy_result.txt", "r") as f:
            deploy_result = f.read().decode("utf-8").strip()
        
        # 下载响应时间
        with sftp.open("/tmp/response_time.txt", "r") as f:
            response_time = f.read().decode("utf-8").strip()
        
        # 下载测试响应
        with sftp.open("/tmp/test_response.txt", "r") as f:
            test_response = f.read().decode("utf-8").strip()
        
        # 下载远程日志
        sftp.get("/tmp/remote_deployment.log", "./remote_deployment.log")
        
        sftp.close()
        
        # 解析结果
        response_time = float(response_time) if response_time else 0.0
        
        if deploy_result == "SUCCESS":
            log("SUCCESS", "部署成功！")
            log("INFO", f"响应时间: {response_time} 秒")
            
            # 解析JSON响应
            try:
                response_json = json.loads(test_response)
                content = response_json.get("choices", [{}])[0].get("message", {}).get("content", "")
                log("INFO", f"测试响应内容: {content.strip()}")
            except json.JSONDecodeError:
                log("INFO", f"测试响应: {test_response}")
        else:
            log("ERROR", f"部署失败: {deploy_result}")
            log("INFO", f"测试响应: {test_response}")
            sys.exit(1)
        
        # 5. 清理服务器上的临时文件
        log("INFO", "清理服务器上的临时文件...")
        ssh.exec_command("rm -f /tmp/vllm_deploy_remote.sh /tmp/deploy_result.txt /tmp/response_time.txt /tmp/test_response.txt /tmp/remote_deployment.log")
        
        # 6. 断开SSH连接
        ssh.close()
        log("INFO", f"已断开与服务器 {server_ip} 的连接")
        
        # 7. 生成测试结果图片
        log("INFO", "生成测试结果图片...")
        
        # 测试结果数据
        test_results = {
            "connection": True,
            "docker_check": True,
            "image_pull": True,
            "container_start": True,
            "service_ready": True,
            "inference_test": deploy_result == "SUCCESS",
            "response_time": response_time,
            "error_message": deploy_result if deploy_result != "SUCCESS" else "",
            "server_info": {
                "host": server_ip,
                "port": port,
                "container_name": container_name
            }
        }
        
        # 计算成功率
        steps = [
            test_results["connection"],
            test_results["docker_check"],
            test_results["image_pull"],
            test_results["container_start"],
            test_results["service_ready"],
            test_results["inference_test"]
        ]
        test_results["success_rate"] = sum(steps) / len(steps) * 100
        
        # 生成SVG图片
        def generate_svg(results, output_path):
            # 测试步骤结果
            steps = ["SSH连接", "Docker检查", "镜像拉取", "容器启动", "服务就绪", "推理测试"]
            results_list = [
                results["connection"],
                results["docker_check"],
                results["image_pull"],
                results["container_start"],
                results["service_ready"],
                results["inference_test"]
            ]
            status = ['成功' if r else '失败' for r in results_list]
            colors = ['#4CAF50' if r else '#F44336' for r in results_list]
            
            # 性能指标
            metrics = ["响应时间 (秒)", "成功率 (%)"]
            values = [
                results["response_time"],
                results["success_rate"]
            ]
            max_value = max(values) * 1.2 if values and max(values) > 0 else 100
            
            # SVG内容
            svg = '''<svg width="800" height="500" xmlns="http://www.w3.org/2000/svg">
                <rect width="800" height="500" fill="white"/>
                <text x="400" y="40" font-family="SimHei, Arial" font-size="24" text-anchor="middle">Qwen3-0.6B vLLM部署测试结果</text>
            '''
            
            # 绘制步骤结果
            svg += '<text x="200" y="80" font-family="SimHei, Arial" font-size="18" text-anchor="middle">部署步骤执行结果</text>'
            for i, (step, color, stat) in enumerate(zip(steps, colors, status)):
                y_pos = 120 + i * 50
                svg += '<rect x="100" y="{0}" width="200" height="30" rx="5" fill="{1}"/>\n'.format(y_pos-20, color)
                svg += '<text x="200" y="{0}" font-family="SimHei, Arial" font-size="14" text-anchor="middle" fill="white">{1}: {2}</text>'.format(y_pos, step, stat)
            
            # 绘制性能指标
            svg += '<text x="600" y="80" font-family="SimHei, Arial" font-size="18" text-anchor="middle">性能指标</text>'
            for i, (metric, value) in enumerate(zip(metrics, values)):
                bar_height = (value / max_value) * 200 if max_value > 0 else 0
                y_pos = 350 - bar_height
                svg += '<rect x="{0}" y="{1}" width="80" height="{2}" rx="5" fill="#3498db"/>\n'.format(500 + i*150, y_pos, bar_height)
                svg += '<text x="{0}" y="370" font-family="SimHei, Arial" font-size="14" text-anchor="middle">{1}</text>'.format(540 + i*150, metric)
                svg += '<text x="{0}" y="{1}" font-family="SimHei, Arial" font-size="14" text-anchor="middle">{2:.2f}</text>'.format(540 + i*150, y_pos-10, value)
            
            # 添加服务器信息
            svg += '<text x="400" y="450" font-family="SimHei, Arial" font-size="14" text-anchor="middle">服务器: {0}</text>'.format(results["server_info"]["host"])
            
            # 添加错误信息
            if results["error_message"]:
                svg += '<text x="400" y="480" font-family="SimHei, Arial" font-size="12" text-anchor="middle" fill="red">错误信息: {0}</text>'.format(results["error_message"])
            
            svg += '</svg>'
            
            # 保存SVG文件
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(svg)
            
            return output_path
        
        try:
            output_path = "./qwen3-06b-test-result.svg"
            generate_svg(test_results, output_path)
            log("SUCCESS", f"测试结果图片已生成: {output_path}")
        except Exception as e:
            log("WARNING", f"生成图片失败: {str(e)}")
            # 生成JSON格式结果
            json_result = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "server_info": test_results["server_info"],
                "test_results": test_results,
                "test_response": test_response
            }
            
            json_path = "./qwen3-06b-test-result.json"
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(json_result, f, ensure_ascii=False, indent=2)
            
            log("SUCCESS", f"JSON格式结果已生成: {json_path}")
        
        log("INFO", "========================================")
        log("SUCCESS", "部署完成！")
        log("INFO", f"服务器: {server_ip}")
        log("INFO", f"模型路径: {model_path}")
        log("INFO", f"服务端口: {port}")
        log("INFO", f"容器名称: {container_name}")
        log("INFO", f"日志文件: {LOG_FILE}")
        log("INFO", f"远程日志: ./remote_deployment.log")
        log("INFO", f"测试结果: ./qwen3-06b-test-result.svg")
        log("INFO", "========================================")
        
    except paramiko.SSHException as e:
        log("ERROR", f"SSH连接失败: {str(e)}")
        sys.exit(1)
    except Exception as e:
        log("ERROR", f"部署过程中发生错误: {str(e)}")
        import traceback
        log("ERROR", f"错误详情: {traceback.format_exc()}")
        sys.exit(1)

# 执行主函数
if __name__ == "__main__":
    main()
