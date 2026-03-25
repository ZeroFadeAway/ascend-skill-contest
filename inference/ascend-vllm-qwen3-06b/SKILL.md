# ascend-vllm-qwen3-06b

## 功能描述
在昇腾NPU服务器上使用vLLM框架部署Qwen3-0.6B模型，支持OpenAI兼容的API接口。

## 适用场景
适用于需要在昇腾910B等NPU设备上快速部署轻量级Qwen3-0.6B模型的场景，支持高效的大语言模型推理。

## 技术栈
- Python 3.11
- Paramiko (SSH连接)
- Docker
- vLLM框架 (昇腾适配版)
- Qwen3-0.6B模型

## 使用方法
### 1. 直接运行
```bash
python .trae/skills/ascend-vllm-qwen3-06b/deploy_qwen3_06b.py
```

### 2. 参数说明
脚本支持以下参数：
- `--hostname`: 服务器地址 (默认: 175.100.2.7)
- `--username`: 登录用户名 (默认: root)
- `--password`: 登录密码 (默认: Huawei@123)
- `--model_path`: 模型权重路径 (默认: /home/zxq/weight/Qwen3-0.6B)
- `--port`: 服务端口 (默认: 8000)
- `--container_name`: 容器名称 (默认: qwen3-06b-vllm)

### 3. 示例
```bash
python .trae/skills/ascend-vllm-qwen3-06b/deploy_qwen3_06b.py --port 8001
```

## 部署流程
1. SSH连接到目标服务器
2. 检查模型权重文件是否存在
3. 检查Docker环境
4. 清理已有容器
5. 启动vLLM容器，挂载模型权重
6. 等待服务初始化
7. 验证服务状态

## 服务验证
部署完成后，可以使用以下命令测试服务：
```bash
curl http://175.100.2.7:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -d '{"model": "/home/zxq/weight/Qwen3-0.6B", "messages": [{"role": "user", "content": "你好"}], "temperature": 0.7}'
```

## 注意事项
1. 确保服务器已安装Docker
2. 确保模型权重路径正确且文件完整
3. 确保服务器有足够的内存和NPU资源
4. 服务初始化可能需要几分钟时间

## 故障排除
- 若容器启动失败，可查看容器日志：`docker logs qwen3-06b-vllm`
- 若端口被占用，可使用`--port`参数指定其他端口
- 若SSH连接失败，检查网络连接和登录凭证