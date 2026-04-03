import inspect
from transformers import Trainer
from trl import ORPOTrainer

def audit_signatures():
    print("Auditing signatures for Trainer vs ORPOTrainer")
    t_methods = {name: func for name, func in inspect.getmembers(Trainer, predicate=inspect.isfunction)}
    o_methods = {name: func for name, func in inspect.getmembers(ORPOTrainer, predicate=inspect.isfunction)}
    
    overridden = [m for m in o_methods if m in t_methods]
    
    for m in overridden:
        t_sig = inspect.signature(t_methods[m])
        o_sig = inspect.signature(o_methods[m])
        if str(t_sig) != str(o_sig):
            print(f"\nMethod mismatch found: {m}")
            print(f"  Trainer:      {t_sig}")
            print(f"  ORPOTrainer:  {o_sig}")

if __name__ == "__main__":
    audit_signatures()
