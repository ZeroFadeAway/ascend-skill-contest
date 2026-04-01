---
name: qwen3-06b-vllm-deployment
description: 在昇腾NPU上使用vLLM部署 Qwen3-0.6B 大语言模型服务。在需要部署vLLM推理服务或在昇腾NPU上运行推理时使用。
---

# Skill: Qwen3-0.6B vLLM部署技能


## 功能描述
使用vLLM框架在昇腾NPU服务器上部署Qwen3-0.6B模型，包含完整的部署流程和测试验证步骤。

## 适用场景
- 快速部署Qwen3-0.6B模型进行推理测试
- 学习vLLM在昇腾NPU上的部署流程
- 需要自动化部署和验证的场景

## 技术栈
- Shell脚本
- Docker
- vLLM框架（昇腾适配版）
- Qwen3-0.6B模型

## 部署流程

### 1. 环境准备
确保服务器已安装Docker并正常运行：
```bash
# 检查Docker是否安装
which docker

# 检查Docker服务状态
systemctl status docker

# 如未安装，执行以下命令安装
sudo apt-get update
sudo apt-get install -y docker.io
sudo systemctl start docker
sudo systemctl enable docker
```

### 2. 镜像拉取
拉取昇腾适配的vLLM镜像：
```bash
export IMAGE=quay.io/ascend/vllm-ascend:v0.17.0rc1
docker pull $IMAGE
```

### 3. 模型路径准备
确保Qwen3-0.6B模型权重已下载到服务器：
```bash
# 示例模型路径
export MODEL_PATH="/home/zxq/weight/Qwen3-0.6B"

# 检查模型路径是否存在
ls -la $MODEL_PATH
```

### 4. 启动vLLM服务
使用Docker启动vLLM推理服务：
```bash
export CONTAINER_NAME="qwen3-06b-vllm"
export PORT=8000

# 清理旧容器
docker rm -f $CONTAINER_NAME 2>/dev/null || true

# 启动新容器
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
    $IMAGE bash -c "export ASCEND_RT_VISIBLE_DEVICES=0; source /usr/local/Ascend/ascend-toolkit/set_env.sh; python -m vllm.entrypoints.openai.api_server --model $MODEL_PATH --host 0.0.0.0 --port $PORT --trust-remote-code --max-model-len 4096 --tensor-parallel-size 1"
```

### 5. 等待服务启动
等待vLLM服务完全启动：
```bash
MAX_WAIT=300
WAIT_COUNT=0
while [ $WAIT_COUNT -lt $MAX_WAIT ]; do
    if netstat -tlnp | grep :$PORT &> /dev/null || lsof -i:$PORT &> /dev/null; then
        echo "服务已在端口 $PORT 监听"
        break
    fi
    
    # 检查容器状态
    if ! docker inspect -f '{{.State.Running}}' $CONTAINER_NAME 2>/dev/null | grep -q "true"; then
        echo "容器已停止，查看日志..."
        docker logs $CONTAINER_NAME
        exit 1
    fi
    
    echo "等待中... ($WAIT_COUNT/$MAX_WAIT秒)"
    sleep 5
    WAIT_COUNT=$((WAIT_COUNT+5))
done

if [ $WAIT_COUNT -ge $MAX_WAIT ]; then
    echo "服务启动超时"
    exit 1
fi
```

### 6. 功能验证
使用curl命令测试模型是否部署成功：
```bash
curl http://localhost:$PORT/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d '{"model": "qwen3-06b", "messages": [{"role": "user", "content": "北京有哪些著名的旅游景点？"}], "temperature": 0.7, "max_tokens": 100}'
```

## 使用方法

### 1. 下载技能
确保技能已下载到本地。

### 2. 执行部署脚本
```bash
# 赋予脚本执行权限
chmod +x .trae/skills/qwen3-06b-vllm-deployment/scripts/deploy.sh

# 执行部署脚本
.trae/skills/qwen3-06b-vllm-deployment/scripts/deploy.sh
```

### 3. 输入必要参数
脚本运行时会提示您输入以下信息：
- 服务器IP地址
- SSH用户名
- SSH密码
- 模型权重路径（可选，默认：/home/zxq/weight/Qwen3-0.6B）
- 服务端口（可选，默认：8000）

### 4. 查看部署结果
部署完成后，脚本会：
- 显示部署状态信息
- 执行模型测试
- 生成测试结果图片

## 参数说明

| 参数 | 默认值 | 描述 |
|------|--------|------|
| 服务器IP | 无 | 目标服务器地址（必填） |
| SSH用户名 | 无 | SSH登录用户名（必填） |
| SSH密码 | 无 | SSH登录密码（必填） |
| 模型路径 | /home/zxq/weight/Qwen3-0.6B | Qwen3-0.6B模型权重路径 |
| 服务端口 | 8000 | vLLM服务端口 |
| 容器名称 | qwen3-06b-vllm | Docker容器名称 |
| 镜像版本 | quay.io/ascend/vllm-ascend:v0.17.0rc1 | vLLM昇腾适配镜像 |

## 错误处理

### 常见问题
1. **Docker未安装**：脚本会自动尝试安装Docker
2. **服务启动超时**：检查容器日志，使用 `docker logs qwen3-06b-vllm`
3. **权限问题**：确保用户有Docker操作权限
4. **端口占用**：使用不同的端口号重新部署

### 日志查看
```bash
# 查看容器日志
docker logs qwen3-06b-vllm

# 查看部署脚本日志
cat deployment.log
```

## 测试结果

部署完成后，脚本会生成以下结果：
1. **文字输出**：部署状态和测试结果
2. **图片报告**：包含部署步骤和性能指标的可视化报告

## 清理资源

如需要停止服务并清理资源：
```bash
# 停止容器
docker stop qwen3-06b-vllm

# 删除容器
docker rm qwen3-06b-vllm

# 删除镜像（可选）
docker rmi quay.io/ascend/vllm-ascend:v0.17.0rc1
```

## 版本信息

- vLLM版本：0.17.0rc1（昇腾适配版）
- 支持模型：Qwen3-0.6B
- 支持平台：昇腾NPU（Atlas 910等）

## 参考文档

- [vLLM官方文档](https://docs.vllm.ai/)
- [昇腾vLLM部署指南](https://docs.vllm.ai/projects/ascend/en/latest/)
- [Qwen3模型文档](https://github.com/QwenLM/Qwen3)
