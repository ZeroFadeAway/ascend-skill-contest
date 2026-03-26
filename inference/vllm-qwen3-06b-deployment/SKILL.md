# vllm-qwen3-06b-deployment

## 功能描述
使用vLLM推理框架在昇腾NPU服务器上部署Qwen3-0.6B模型，支持OpenAI兼容的API接口。

## 适用场景
- 框架部署初学者的自动化部署指导
- Agentic Coding场景下的端到端环境搭建
- 需要在昇腾NPU上快速部署轻量级大语言模型的场景

## 技术栈
- Python 3.8+
- Docker
- vLLM框架（昇腾适配版）
- Qwen3-0.6B模型

## 使用方法
### 基本用法
```bash
python .trae/skills/vllm-qwen3-06b-deployment/scripts/deploy.py
```

### 参数说明
| 参数 | 默认值 | 描述 |
|------|--------|------|
| `--host` | 无 | 目标服务器地址（必填） |
| `--user` | 无 | SSH登录用户名（必填） |
| `--password` | 无 | SSH登录密码（必填） |
| `--model-path` | `/home/zxq/weight/Qwen3-0.6B` | 模型权重路径 |
| `--port` | `8000` | 服务端口 |
| `--container-name` | `qwen3-06b-vllm` | Docker容器名称 |

### 示例
```bash
# 基本部署（必填参数）
python scripts/deploy.py --host 服务器IP --user 用户名 --password 密码

# 自定义参数部署
python scripts/deploy.py --host 服务器IP --user 用户名 --password 密码 --port 8001 --model-path /path/to/model
```

## 部署流程
1. **SSH连接验证**：连接到目标服务器
2. **模型检查**：验证模型权重文件存在性
3. **环境准备**：检查Docker是否安装
4. **容器管理**：清理已有容器（如果存在）
5. **服务启动**：启动vLLM容器并挂载模型
6. **初始化等待**：等待服务完成初始化
7. **状态验证**：检查服务是否正常运行

## 服务验证
部署完成后，可通过以下命令测试：
```bash
curl http://175.100.2.7:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -d '{"model": "/home/zxq/weight/Qwen3-0.6B", "messages": [{"role": "user", "content": "你好"}], "temperature": 0.7}'
```

## 错误处理
- **连接失败**：检查网络连接、服务器地址和登录凭证
- **模型缺失**：确认模型路径正确且文件完整
- **端口占用**：使用`--port`参数指定其他端口
- **容器问题**：查看容器日志 `docker logs qwen3-06b-vllm`

## 注意事项
- 建议使用镜像部署，避免源码构建的复杂性
- 部署时间约30分钟以内
- 确保服务器有足够的NPU资源和内存
- 首次使用需接受Docker镜像许可
