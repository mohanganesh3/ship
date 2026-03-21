import sys, torch, transformers, peft, trl
print('python:', sys.version.split()[0])
print('torch:', torch.__version__)
print('cuda_available:', torch.cuda.is_available())  # should be True but we will NOT use it
print('transformers:', transformers.__version__)
print('peft:', peft.__version__)
print('trl:', trl.__version__)

a = torch.randn(1024, 1024, dtype=torch.float32)
b = torch.randn(1024, 1024, dtype=torch.float32)
c = a @ b
print('cpu_matmul_ok:', c.shape)

from transformers import AutoModelForCausalLM, AutoTokenizer
tokenizer = AutoTokenizer.from_pretrained('models/student-1.7b', trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained('models/student-1.7b', torch_dtype=torch.float32, device_map='cpu', trust_remote_code=True)
print('model_loaded_params_B:', sum(p.numel() for p in model.parameters())/1e9)
print('ram_used_GB:', model.get_memory_footprint()/1e9)
del model
import gc; gc.collect()
print('ENV_CHECK_PASS')
