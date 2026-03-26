#!/usr/bin/env python3
"""
Qwen3-0.6B模型vLLM部署脚本
符合ascend-skill-contest题目1要求
"""

import paramiko
import argparse
import logging
import time

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('deployment.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class VLLMDeployer:
    """vLLM模型部署器"""
    
    def __init__(self, host, user, password):
        self.host = host
        self.user = user
        self.password = password
        self.ssh_client = None
    
    def connect(self):
        """建立SSH连接"""
        try:
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh_client.connect(self.host, 22, self.user, self.password, timeout=30)
            logger.info(f"✅ 成功连接到服务器: {self.host}")
            return True
        except Exception as e:
            logger.error(f"❌ SSH连接失败: {str(e)}")
            return False
    
    def disconnect(self):
        """断开SSH连接"""
        if self.ssh_client:
            self.ssh_client.close()
            logger.info("✅ SSH连接已关闭")
    
    def run_command(self, command, timeout=60):
        """执行SSH命令"""
        if not self.ssh_client:
            logger.error("❌ SSH客户端未连接")
            return None
        
        try:
            stdin, stdout, stderr = self.ssh_client.exec_command(command, timeout=timeout)
            output = stdout.read().decode('utf-8')
            error = stderr.read().decode('utf-8')
            exit_code = stdout.channel.recv_exit_status()
            
            return {
                'success': exit_code == 0,
                'output': output,
                'error': error,
                'exit_code': exit_code
            }
        except Exception as e:
            logger.error(f"❌ 命令执行失败: {str(e)}")
            return None
    
    def check_model(self, model_path):
        """检查模型文件"""
        logger.info(f"🔍 检查模型路径: {model_path}")
        
        # 检查路径是否存在
        result = self.run_command(f"ls -la {model_path}")
        if not result or not result['success']:
            logger.error(f"❌ 模型路径不存在: {model_path}")
            return False
        
        # 检查关键文件
        required_files = ['model.safetensors', 'config.json', 'tokenizer.json']
        for file in required_files:
            result = self.run_command(f"ls -la {model_path}/{file} 2>/dev/null")
            if not result or not result['success']:
                logger.warning(f"⚠️  缺少模型文件: {file}")
        
        logger.info("✅ 模型路径验证通过")
        return True
    
    def check_docker(self):
        """检查Docker环境"""
        logger.info("🔍 检查Docker环境")
        
        result = self.run_command("docker --version")
        if not result or not result['success']:
            logger.error("❌ Docker未安装")
            return False
        
        logger.info(f"✅ Docker已安装: {result['output'].strip()}")
        return True
    
    def cleanup_container(self, container_name):
        """清理已有容器"""
        logger.info(f"🧹 清理容器: {container_name}")
        
        result = self.run_command(f"docker rm -f {container_name} 2>/dev/null || true")
        if result and result['success']:
            logger.info("✅ 容器清理完成")
        else:
            logger.warning(f"⚠️  容器清理失败: {result['error'] if result else '未知错误'}")
    
    def start_container(self, container_name, model_path, port):
        """启动vLLM容器"""
        logger.info(f"🚀 启动容器: {container_name}")
        
        # 使用昇腾适配的vLLM镜像
        docker_cmd = f"docker run -d --name {container_name} \
  --device /dev/davinci0:/dev/davinci0 --device /dev/davinci_manager:/dev/davinci_manager \
  --ipc=host --net=host \
  -v {model_path}:{model_path} \
  quay.io/ascend/vllm-ascend:v0.17.0rc1 \
  bash -c 'sleep infinity'"
        
        result = self.run_command(docker_cmd)
        if not result or not result['success']:
            logger.error(f"❌ 容器启动失败: {result['error']}")
            return False
        
        container_id = result['output'].strip()
        logger.info(f"✅ 容器启动成功，ID: {container_id}")
        
        # 在容器内启动vLLM服务
        vllm_cmd = f"""docker exec -d {container_name} bash -c 'source /usr/local/Ascend/ascend-toolkit/set_env.sh && python -m vllm.entrypoints.openai.api_server --model {model_path} --port {port} --trust-remote-code --tensor-parallel-size 1 --max-model-len 4096 > /tmp/vllm.log 2>&1'"""
        
        result = self.run_command(vllm_cmd)
        if not result or not result['success']:
            logger.error(f"❌ vLLM服务启动失败: {result['error']}")
            return False
        
        logger.info(f"✅ vLLM服务已在后台启动，端口: {port}")
        return True
    
    def wait_for_service(self, container_name, port, timeout=300):
        """等待服务初始化完成"""
        logger.info(f"⏳ 等待服务初始化... (最长{timeout/60:.1f}分钟)")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            # 检查服务端口
            result = self.run_command(f"docker exec {container_name} netstat -tlnp 2>/dev/null | grep {port}")
            if result and result['success'] and result['output']:
                logger.info("✅ 服务已成功启动")
                return True
            
            # 检查日志是否有错误
            result = self.run_command(f"docker exec {container_name} cat /tmp/vllm.log 2>/dev/null | tail -n 20")
            if result and result['success']:
                if "ERROR" in result['output'] and "Failed" in result['output']:
                    logger.error(f"❌ 服务启动失败: {result['output']}")
                    return False
            
            time.sleep(10)
        
        logger.warning(f"⚠️  服务初始化超时({timeout}秒)")
        return False
    
    def test_service(self, host, port, model_path):
        """测试服务可用性"""
        logger.info("🧪 测试服务可用性")
        
        # 创建测试命令，使用单引号和转义
        test_cmd = "curl -s -X POST http://" + host + ":" + str(port) + "/v1/chat/completions " \
                  + "-H 'Content-Type: application/json' " \
                  + "-H 'Authorization: Bearer your-api-key' " \
                  + "-d '{\"model\": \"" + model_path + "\", \"messages\": [{\"role\": \"user\", \"content\": \"你好\"}], \"temperature\": 0.7}'"
        
        result = self.run_command(test_cmd, timeout=120)
        if result and result['success']:
            logger.info(f"✅ API测试成功: {result['output'][:100]}...")
            return True
        else:
            logger.warning(f"⚠️  API测试失败: {result['error'] if result else '未知错误'}")
            return False

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='在昇腾NPU上部署Qwen3-0.6B模型')
    
    parser.add_argument('--host', type=str, required=True,
                       help='目标服务器地址 (必填)')
    parser.add_argument('--user', type=str, required=True,
                       help='SSH登录用户名 (必填)')
    parser.add_argument('--password', type=str, required=True,
                       help='SSH登录密码 (必填)')
    parser.add_argument('--model-path', type=str, default='/home/zxq/weight/Qwen3-0.6B',
                       help='模型权重路径 (默认: /home/zxq/weight/Qwen3-0.6B)')
    parser.add_argument('--port', type=int, default=8000,
                       help='服务端口 (默认: 8000)')
    parser.add_argument('--container-name', type=str, default='qwen3-06b-vllm',
                       help='容器名称 (默认: qwen3-06b-vllm)')
    
    return parser.parse_args()

def main():
    """主函数"""
    args = parse_args()
    
    logger.info("="*60)
    logger.info("Qwen3-0.6B模型vLLM部署")
    logger.info("="*60)
    
    deployer = VLLMDeployer(args.host, args.user, args.password)
    
    try:
        # 1. 连接服务器
        if not deployer.connect():
            return 1
        
        # 2. 检查模型
        if not deployer.check_model(args.model_path):
            return 1
        
        # 3. 检查Docker
        if not deployer.check_docker():
            return 1
        
        # 4. 清理容器
        deployer.cleanup_container(args.container_name)
        
        # 5. 启动容器
        if not deployer.start_container(args.container_name, args.model_path, args.port):
            return 1
        
        # 6. 等待服务
        if not deployer.wait_for_service(args.container_name, args.port):
            return 1
        
        # 7. 测试服务
        deployer.test_service(args.host, args.port, args.model_path)
        
        logger.info("="*60)
        logger.info("部署完成!")
        logger.info(f"服务器: {args.host}")
        logger.info(f"端口: {args.port}")
        logger.info(f"容器: {args.container_name}")
        logger.info(f"模型: {args.model_path}")
        logger.info("="*60)
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("⚠️  部署被用户中断")
        return 1
    finally:
        deployer.disconnect()

if __name__ == "__main__":
    exit(main())
