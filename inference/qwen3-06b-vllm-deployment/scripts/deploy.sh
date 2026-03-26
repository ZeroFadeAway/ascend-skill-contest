#!/bin/bash

# Qwen3-0.6B vLLM部署脚本
# 用于在昇腾NPU上部署Qwen3-0.6B模型并验证

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志文件
LOG_FILE="deployment.log"

# 初始化日志
log() {
    local level="$1"
    local message="$2"
    local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    
    case $level in
        "INFO")
            echo -e "${timestamp} - ${BLUE}[INFO]${NC} ${message}" | tee -a $LOG_FILE
            ;;
        "SUCCESS")
            echo -e "${timestamp} - ${GREEN}[SUCCESS]${NC} ${message}" | tee -a $LOG_FILE
            ;;
        "WARNING")
            echo -e "${timestamp} - ${YELLOW}[WARNING]${NC} ${message}" | tee -a $LOG_FILE
            ;;
        "ERROR")
            echo -e "${timestamp} - ${RED}[ERROR]${NC} ${message}" | tee -a $LOG_FILE
            ;;
        *)
            echo -e "${timestamp} - [UNKNOWN] ${message}" | tee -a $LOG_FILE
            ;;
    esac
}

# 清理临时文件
cleanup() {
    log "INFO" "清理临时文件..."
    rm -f /tmp/vllm_deploy_remote.sh
    log "SUCCESS" "临时文件清理完成"
}

trap cleanup EXIT

# 主函数
main() {
    log "INFO" "========================================"
    log "INFO" "Qwen3-0.6B vLLM部署脚本"
    log "INFO" "========================================"
    
    # 1. 获取用户输入
    log "INFO" "请输入部署参数："
    
    # 服务器IP
    read -p "服务器IP地址: " SERVER_IP
    if [ -z "$SERVER_IP" ]; then
        log "ERROR" "服务器IP地址不能为空"
        exit 1
    fi
    
    # SSH用户名
    read -p "SSH用户名: " SSH_USER
    if [ -z "$SSH_USER" ]; then
        log "ERROR" "SSH用户名不能为空"
        exit 1
    fi
    
    # SSH密码
    read -s -p "SSH密码: " SSH_PASSWORD
    echo
    if [ -z "$SSH_PASSWORD" ]; then
        log "ERROR" "SSH密码不能为空"
        exit 1
    fi
    
    # 模型路径（可选）
    read -p "模型权重路径 [默认: /home/zxq/weight/Qwen3-0.6B]: " MODEL_PATH
    MODEL_PATH=${MODEL_PATH:-"/home/zxq/weight/Qwen3-0.6B"}
    
    # 服务端口（可选）
    read -p "服务端口 [默认: 8000]: " PORT
    PORT=${PORT:-8000}
    
    # 容器名称（可选）
    read -p "容器名称 [默认: qwen3-06b-vllm]: " CONTAINER_NAME
    CONTAINER_NAME=${CONTAINER_NAME:-"qwen3-06b-vllm"}
    
    log "SUCCESS" "参数输入完成"
    log "INFO" "服务器IP: $SERVER_IP"
    log "INFO" "SSH用户名: $SSH_USER"
    log "INFO" "模型路径: $MODEL_PATH"
    log "INFO" "服务端口: $PORT"
    log "INFO" "容器名称: $CONTAINER_NAME"
    
    # 2. 创建远程部署脚本
    log "INFO" "创建远程部署脚本..."
    
    cat > /tmp/vllm_deploy_remote.sh << 'EOF'
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
MODEL_PATH="$1"
PORT="$2"
CONTAINER_NAME="$3"
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

# 测试推理功能
log "INFO" "测试推理功能..."

# 记录开始时间
START_TIME=$(date +%s.%N)

# 发送测试请求
RESPONSE=$(curl -s -X POST http://localhost:$PORT/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d '{"model": "qwen3-06b", "messages": [{"role": "user", "content": "北京有哪些著名的旅游景点？"}], "temperature": 0.7, "max_tokens": 100}')

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
EOF
    
    chmod +x /tmp/vllm_deploy_remote.sh
    log "SUCCESS" "远程部署脚本创建完成"
    
    # 3. 上传脚本到服务器并执行
    log "INFO" "上传脚本到服务器..."
    
    # 使用sshpass上传脚本
    if ! command -v sshpass &> /dev/null; then
        log "WARNING" "sshpass未安装，尝试手动安装..."
        if command -v apt-get &> /dev/null; then
            apt-get update &>> $LOG_FILE
            apt-get install -y sshpass &>> $LOG_FILE
        elif command -v yum &> /dev/null; then
            yum install -y sshpass &>> $LOG_FILE
        else
            log "ERROR" "无法安装sshpass，请手动安装后重试"
            exit 1
        fi
    fi
    
    # 上传脚本
    sshpass -p "$SSH_PASSWORD" scp -o StrictHostKeyChecking=no /tmp/vllm_deploy_remote.sh $SSH_USER@$SERVER_IP:/tmp/ &>> $LOG_FILE
    
    if [ $? -eq 0 ]; then
        log "SUCCESS" "脚本上传成功"
    else
        log "ERROR" "脚本上传失败，请检查网络连接和服务器信息"
        exit 1
    fi
    
    # 4. 执行远程部署
    log "INFO" "执行远程部署..."
    log "INFO" "这可能需要几分钟时间，请耐心等待..."
    
    sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no $SSH_USER@$SERVER_IP "bash /tmp/vllm_deploy_remote.sh '$MODEL_PATH' '$PORT' '$CONTAINER_NAME'" &>> $LOG_FILE
    
    if [ $? -eq 0 ]; then
        log "SUCCESS" "远程部署脚本执行完成"
    else
        log "ERROR" "远程部署脚本执行失败"
        # 获取远程日志
        sshpass -p "$SSH_PASSWORD" scp -o StrictHostKeyChecking=no $SSH_USER@$SERVER_IP:/tmp/remote_deployment.log ./remote_deployment.log &>> $LOG_FILE
        log "INFO" "远程日志已下载到: ./remote_deployment.log"
        exit 1
    fi
    
    # 5. 获取测试结果
    log "INFO" "获取测试结果..."
    
    # 下载结果文件
    sshpass -p "$SSH_PASSWORD" scp -o StrictHostKeyChecking=no $SSH_USER@$SERVER_IP:/tmp/deploy_result.txt /tmp/ &>> $LOG_FILE
    sshpass -p "$SSH_PASSWORD" scp -o StrictHostKeyChecking=no $SSH_USER@$SERVER_IP:/tmp/response_time.txt /tmp/ &>> $LOG_FILE
    sshpass -p "$SSH_PASSWORD" scp -o StrictHostKeyChecking=no $SSH_USER@$SERVER_IP:/tmp/test_response.txt /tmp/ &>> $LOG_FILE
    sshpass -p "$SSH_PASSWORD" scp -o StrictHostKeyChecking=no $SSH_USER@$SERVER_IP:/tmp/remote_deployment.log ./remote_deployment.log &>> $LOG_FILE
    
    # 解析结果
    DEPLOY_RESULT=$(cat /tmp/deploy_result.txt)
    RESPONSE_TIME=$(cat /tmp/response_time.txt 2>/dev/null || echo "0")
    TEST_RESPONSE=$(cat /tmp/test_response.txt 2>/dev/null || echo "")
    
    if [ "$DEPLOY_RESULT" = "SUCCESS" ]; then
        log "SUCCESS" "部署成功！"
        log "INFO" "响应时间: $RESPONSE_TIME 秒"
        log "INFO" "测试响应: $(echo "$TEST_RESPONSE" | grep -o '"content": "[^"]*' | head -1 | cut -d '"' -f 4 | cut -c 1-50)..."
    else
        log "ERROR" "部署失败: $DEPLOY_RESULT"
        log "INFO" "测试响应: $TEST_RESPONSE"
        exit 1
    fi
    
    # 6. 生成测试结果图片
    log "INFO" "生成测试结果图片..."
    
    # 创建Python脚本生成SVG图片
    cat > /tmp/generate_result.py << 'EOF'
#!/usr/bin/env python3
import json
import sys

# 测试结果数据
results = {
    "connection": True,
    "docker_check": True,
    "image_pull": True,
    "container_start": True,
    "service_ready": True,
    "inference_test": True if "$DEPLOY_RESULT" == "SUCCESS" else False,
    "response_time": float("$RESPONSE_TIME"),
    "error_message": "$DEPLOY_RESULT" if "$DEPLOY_RESULT" != "SUCCESS" else "",
    "server_info": {
        "host": "$SERVER_IP",
        "port": "$PORT",
        "container_name": "$CONTAINER_NAME"
    }
}

# 计算成功率
steps = [
    results["connection"],
    results["docker_check"],
    results["image_pull"],
    results["container_start"],
    results["service_ready"],
    results["inference_test"]
]
results["success_rate"] = sum(steps) / len(steps) * 100

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
    
    print(f"测试结果图片已生成: {output_path}")

# 执行生成
if __name__ == "__main__":
    output_path = sys.argv[1] if len(sys.argv) > 1 else "./qwen3-06b-test-result.svg"
    generate_svg(results, output_path)
EOF
    
    # 替换脚本中的变量
    sed -i "s/\$DEPLOY_RESULT/$DEPLOY_RESULT/g" /tmp/generate_result.py
    sed -i "s/\$RESPONSE_TIME/$RESPONSE_TIME/g" /tmp/generate_result.py
    sed -i "s/\$SERVER_IP/$SERVER_IP/g" /tmp/generate_result.py
    sed -i "s/\$PORT/$PORT/g" /tmp/generate_result.py
    sed -i "s/\$CONTAINER_NAME/$CONTAINER_NAME/g" /tmp/generate_result.py
    
    # 执行Python脚本生成图片
    python3 /tmp/generate_result.py ./qwen3-06b-test-result.svg &>> $LOG_FILE
    
    if [ $? -eq 0 ]; then
        log "SUCCESS" "测试结果图片已生成: ./qwen3-06b-test-result.svg"
    else
        log "WARNING" "生成图片失败，将生成JSON格式结果"
        # 生成JSON结果
        cat > ./qwen3-06b-test-result.json << EOF
{
  "timestamp": "$(date +"%Y-%m-%d %H:%M:%S")",
  "server_info": {
    "host": "$SERVER_IP",
    "port": "$PORT",
    "container_name": "$CONTAINER_NAME"
  },
  "test_results": {
    "connection": true,
    "docker_check": true,
    "image_pull": true,
    "container_start": true,
    "service_ready": true,
    "inference_test": $(echo "$DEPLOY_RESULT" | grep -q "SUCCESS" && echo "true" || echo "false"),
    "response_time": $RESPONSE_TIME,
    "success_rate": $(echo "scale=2; $(echo "$DEPLOY_RESULT" | grep -q "SUCCESS" && echo "6" || echo "5")/6*100" | bc),
    "error_message": "$(echo "$DEPLOY_RESULT" | grep -q "SUCCESS" && echo "" || echo "$DEPLOY_RESULT")"
  },
  "test_response": "$TEST_RESPONSE"
}
EOF
        log "SUCCESS" "JSON格式结果已生成: ./qwen3-06b-test-result.json"
    fi
    
    # 7. 清理服务器上的临时文件
    log "INFO" "清理服务器上的临时文件..."
    sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no $SSH_USER@$SERVER_IP "rm -f /tmp/vllm_deploy_remote.sh /tmp/deploy_result.txt /tmp/response_time.txt /tmp/test_response.txt /tmp/remote_deployment.log" &>> $LOG_FILE
    
    log "INFO" "========================================"
    log "SUCCESS" "部署完成！"
    log "INFO" "服务器: $SERVER_IP"
    log "INFO" "模型路径: $MODEL_PATH"
    log "INFO" "服务端口: $PORT"
    log "INFO" "容器名称: $CONTAINER_NAME"
    log "INFO" "测试结果: ./qwen3-06b-test-result.svg"
    log "INFO" "日志文件: ./deployment.log"
    log "INFO" "远程日志: ./remote_deployment.log"
    log "INFO" "========================================"
}

# 执行主函数
main
