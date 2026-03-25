import paramiko
import time
import argparse
import sys
import logging

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('.trae/skills/ascend-vllm-qwen3-06b/deployment.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def run_ssh_command(hostname, username, password, command, timeout=60):
    """
    在远程服务器上执行SSH命令
    """
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname, 22, username, password, timeout=30)
        
        stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
        output = stdout.read().decode('utf-8')
        error = stderr.read().decode('utf-8')
        exit_code = stdout.channel.recv_exit_status()
        
        client.close()
        
        return {
            'success': exit_code == 0,
            'output': output,
            'error': error,
            'exit_code': exit_code
        }
    except Exception as e:
        return {
            'success': False,
            'output': '',
            'error': str(e),
            'exit_code': -1
        }

def deploy_qwen3_06b(args):
    """
    部署Qwen3-0.6B模型到昇腾服务器
    """
    logger.info("="*60)
    logger.info("Qwen3-0.6B模型部署到昇腾服务器")
    logger.info("="*60)
    
    # 1. 检查服务器连接
    logger.info(f"\n1. 检查服务器连接: {args.hostname}")
    result = run_ssh_command(args.hostname, args.username, args.password, "echo '连接成功'")
    if not result['success']:
        logger.error(f"❌ 服务器连接失败: {result['error']}")
        return False
    logger.info("✅ 服务器连接成功")
    
    # 2. 检查模型权重文件
    logger.info(f"\n2. 检查模型权重: {args.model_path}")
    result = run_ssh_command(args.hostname, args.username, args.password, f"ls -la {args.model_path}")
    if not result['success']:
        logger.error(f"❌ 模型权重检查失败: {result['error']}")
        return False
    
    logger.info("✅ 模型权重文件存在")
    # 显示权重文件
    for line in result['output'].split('\n'):
        if any(ext in line for ext in ['.safetensors', '.bin', '.pt']):
            logger.info(f"   - {line.strip()}")
    
    # 3. 检查Docker环境
    logger.info(f"\n3. 检查Docker环境")
    result = run_ssh_command(args.hostname, args.username, args.password, "docker --version")
    if not result['success']:
        logger.error(f"❌ Docker未安装或不可用: {result['error']}")
        return False
    logger.info(f"✅ Docker已安装: {result['output'].strip()}")
    
    # 4. 停止并删除已有容器
    logger.info(f"\n4. 清理已有容器: {args.container_name}")
    result = run_ssh_command(args.hostname, args.username, args.password, f"docker rm -f {args.container_name} 2>/dev/null || true")
    logger.info(f"✅ 已清理容器")
    
    # 5. 启动容器（两阶段启动）
    logger.info(f"\n5. 启动模型服务容器")
    
    # 第一阶段：启动一个后台运行的容器
    docker_run_cmd = f"docker run -d --name {args.container_name} \
  --device /dev/davinci0:/dev/davinci0 --device /dev/davinci_manager:/dev/davinci_manager \
  --ipc=host --net=host \
  -v {args.model_path}:{args.model_path} \
  quay.io/ascend/vllm-ascend:v0.17.0rc1 \
  bash -c 'sleep infinity'"
    
    result = run_ssh_command(args.hostname, args.username, args.password, docker_run_cmd)
    if not result['success']:
        logger.error(f"❌ 容器启动失败: {result['error']}")
        return False
    
    container_id = result['output'].strip()
    logger.info(f"✅ 容器启动成功")
    logger.info(f"   容器ID: {container_id}")
    logger.info(f"   容器名称: {args.container_name}")
    
    # 第二阶段：在容器内执行模型服务启动命令
    logger.info(f"\n6. 在容器内启动模型服务")
    model_start_cmd = f"docker exec -d {args.container_name} \
  bash -c 'source /usr/local/Ascend/ascend-toolkit/set_env.sh && \
  source /usr/local/Ascend/cann-8.5.1/share/info/ascendnpu-ir/bin/set_env.sh && \
  source /usr/local/Ascend/nnal/atb/set_env.sh && \
  python -m vllm.entrypoints.openai.api_server \
  --model {args.model_path} \
  --tensor-parallel-size 1 \
  --max-model-len 4096 \
  --trust-remote-code \
  --dtype fp16 \
  --port {args.port}'"
    
    result = run_ssh_command(args.hostname, args.username, args.password, model_start_cmd)
    if not result['success']:
        logger.error(f"❌ 模型服务启动失败: {result['error']}")
        return False
    
    logger.info(f"✅ 模型服务已在容器内启动")
    logger.info(f"   服务端口: {args.port}")
    logger.info(f"   模型路径: {args.model_path}")
    
    # 7. 等待服务初始化
    logger.info(f"\n7. 等待服务初始化... (约90秒)")
    time.sleep(90)
    
    # 8. 检查服务状态
    logger.info(f"\n8. 检查服务状态")
    
    # 检查容器是否运行
    result = run_ssh_command(args.hostname, args.username, args.password, f"docker ps -a | grep {args.container_name}")
    if not result['success'] or "Exited" in result['output']:
        logger.error(f"❌ 容器已停止: {result['output']}")
        # 查看容器日志
        log_result = run_ssh_command(args.hostname, args.username, args.password, f"docker logs {args.container_name} | tail -n 50")
        if log_result['output']:
            logger.info(f"\n容器日志:")
            logger.info(log_result['output'])
        return False
    
    logger.info(f"✅ 容器正在运行: {result['output'].strip()}")
    
    # 检查端口监听
    result = run_ssh_command(args.hostname, args.username, args.password, f"netstat -tuln | grep :{args.port}")
    if result['success'] and result['output']:
        logger.info(f"✅ 端口 {args.port} 已监听")
    else:
        logger.warning(f"⚠️  端口 {args.port} 未监听，检查进程")
        
    # 检查Python进程
    result = run_ssh_command(args.hostname, args.username, args.password, f"docker exec {args.container_name} ps aux | grep python")
    if result['success'] and result['output']:
        logger.info(f"✅ Python进程正在运行")
        for line in result['output'].split('\n'):
            if line.strip():
                logger.info(f"   {line.strip()}")
    else:
        logger.warning(f"⚠️  未找到Python进程: {result['error']}")
    
    # 查看服务日志
    logger.info(f"\n8. 查看服务日志 (最近30行)")
    result = run_ssh_command(args.hostname, args.username, args.password, f"docker logs {args.container_name} | tail -n 30")
    if result['output']:
        logger.info(result['output'])
    else:
        logger.warning(f"⚠️  未获取到服务日志: {result['error']}")
    
    # 尝试访问API
    logger.info(f"\n9. 测试API访问")
    api_cmd = f"curl -s -H 'Authorization: Bearer your-api-key' http://localhost:{args.port}/v1/models"
    result = run_ssh_command(args.hostname, args.username, args.password, api_cmd, timeout=15)
    if result['success'] and result['output']:
        logger.info(f"✅ API可访问")
    else:
        logger.warning(f"⚠️  API访问失败: {result['error']}")
    
    logger.info("\n" + "="*60)
    logger.info("部署完成!")
    logger.info("="*60)
    logger.info(f"服务器地址: {args.hostname}")
    logger.info(f"服务端口: {args.port}")
    logger.info(f"容器名称: {args.container_name}")
    logger.info(f"模型路径: {args.model_path}")
    logger.info("\n测试命令:")
    logger.info(f"curl http://{args.hostname}:{args.port}/v1/chat/completions \\")
    logger.info(f"  -H 'Content-Type: application/json' \\")
    logger.info(f"  -H 'Authorization: Bearer your-api-key' \\")
    logger.info(f"  -d '{{\"model\": \"{args.model_path}\", \"messages\": [{{\"role\": \"user\", \"content\": \"你好\"}}], \"temperature\": 0.7}}'")
    
    return True

def main():
    """
    主函数，处理命令行参数
    """
    parser = argparse.ArgumentParser(description="在昇腾NPU上部署Qwen3-0.6B模型")
    
    parser.add_argument('--hostname', type=str, default='175.100.2.7',
                       help='服务器地址 (默认: 175.100.2.7)')
    parser.add_argument('--username', type=str, default='root',
                       help='登录用户名 (默认: root)')
    parser.add_argument('--password', type=str, default='Huawei@123',
                       help='登录密码 (默认: Huawei@123)')
    parser.add_argument('--model_path', type=str, default='/home/zxq/weight/Qwen3-0.6B',
                       help='模型权重路径 (默认: /home/zxq/weight/Qwen3-0.6B)')
    parser.add_argument('--port', type=int, default=8000,
                       help='服务端口 (默认: 8000)')
    parser.add_argument('--container_name', type=str, default='qwen3-06b-vllm',
                       help='容器名称 (默认: qwen3-06b-vllm)')
    
    args = parser.parse_args()
    
    success = deploy_qwen3_06b(args)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()