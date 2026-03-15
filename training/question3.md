# 题目 3：模型迁移（GPU → 昇腾 NPU）

**PyTorch Examples 官方仓库：**

[examples/distributed/FSDP2 at main · pytorch/examples](https://github.com/pytorch/examples/tree/main/distributed/FSDP2)

## 题目概览

|   项目   |  说明   |
| :------: | :-----: |
|   难度   | ⭐⭐ 中等  |
| 预估时长 | 90 分钟 |

------

## 使用场景

- 帮助对于Pytorch分布式训练不熟悉的同学，快速将训练任务从 GPU 迁移到 NPU
- 在 Agentic Coding 场景中，通过 AI 端到端完成 NPU 训练环境适配与任务迁移验证

## 任务描述

将 PyTorch Examples 仓库中**FSDP2 的 nanoGPT 训练任务**，从 GPU 环境迁移到 NPU 环境，完成训练流程

**基本要求：**

1. 适配 NPU 环境：安装对应的torch/torch_npu环境（推荐2.7版本以上）
2. 接入`torch_npu.npu_fusion_attention`融合算子
3. 启动多卡训练：使用`torchrun`启动 NPU 分布式训练（ ≥ 2 卡 )
4. 验证训练流程：第一次训练完成后，可保存checkpoints；第二次训练可以加载checkpoints

## 具体要求

|   项目   |                             说明                             |
| :------: | :----------------------------------------------------------: |
|  Prompt  | 需包含引导 Agent 完成 “代码适配→训练启动→checkpoint 验证” 的全流程指令 |
| 执行时间 |                          30分钟以内                          |

## 输出要求

参赛者需提交：

**目录结构**

```
skill-name/
├── SKILL.md        # 必须
├── reference/      # 可选
└── scripts/        # 可选
```

## 评分标准

参考 [Agent Skill 创作最佳实践](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)：

| 维度             | 权重 | 说明                                                         |
| ---------------- | ---- | ------------------------------------------------------------ |
| 功能完整性       | 60%  | 是否能成功引导完成 nanoGPT 训练流程                          |
| description 质量 | 20%  | 是否包含 WHAT（做什么）和 WHEN（何时触发）；是否具体、含关键词；是否用第三人称 |
| 指令与结构       | 10%  | SKILL.md 是否简洁（建议 500 行以内）；指令步骤是否清晰可执行；是否合理使用渐进式披露 |
| 代码与脚本       | 10%  | 脚本是否明确列出依赖；路径是否使用正斜杠；错误处理是否清晰；是否避免推卸给 Agent |