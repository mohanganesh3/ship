# RANKING EVALUATION: Reinforcement Learning Methods (GRPO / DPO / ORPO / RLVR / KTO / SimPO / SPIN)

**Approach Under Evaluation:** Applying post-training reinforcement learning and preference optimization methods to a small model (1-3B) to improve the quality, accuracy, and reliability of its maritime domain answers. These methods include Direct Preference Optimization (DPO), Group Relative Policy Optimization (GRPO), Odds Ratio Preference Optimization (ORPO), RL from Verifiable Rewards (RLVR), Kahneman-Tversky Optimization (KTO), Simple Preference Optimization (SimPO), and Self-Play Fine-tuning (SPIN).

**Evaluator:** Ranking Agent  
**Date:** February 16, 2026  
**Target:** Maritime chatbot on mobile phones, NO RAG, all knowledge baked into weights  
**Model Size Constraint:** 1-3B parameters  
**Deployment:** ARM CPU, 3-6GB RAM, iOS/Android  

---

## RESEARCH SOURCES ANALYZED

| Paper / Resource | Key Finding for This Evaluation |
|---|---|
| **DPO — "Direct Preference Optimization: Your Language Model is Secretly a Reward Model"** (Rafailov et al., 2023; arXiv:2305.18290) | Replaces RLHF with a simple classification loss on preference pairs (chosen vs rejected). Stable, performant, computationally lightweight. Eliminates need for reward model and RL sampling. Exceeds PPO-based RLHF on sentiment control, matches on summarization and dialog quality. **But the paper's benchmarks are entirely about style, tone, and helpfulness — NOT factual knowledge retention.** |
| **GRPO — "DeepSeekMath: Pushing the Limits of Mathematical Reasoning"** (Shao et al., 2024; arXiv:2402.03300) | Introduces Group Relative Policy Optimization — generates N candidate solutions per problem, scores them against ground truth, and reinforces the best within each group. Eliminates the separate critic/value model, reducing VRAM by ~50% vs PPO. DeepSeekMath-7B achieves 51.7% on MATH benchmark. **Critical: GRPO works on MATH because answers are verifiable (correct/incorrect). Maritime factual QA lacks clean verifiability unless hand-engineered.** |
| **DeepSeek-R1** (DeepSeek-AI, 2025; arXiv:2501.12948; Nature 2025) | 671B MoE model trained via pure RL (GRPO) develops emergent reasoning (self-verification, reflection, dynamic strategy adaptation). Distilled to Qwen-1.5B via 800K reasoning traces → 83.9% MATH-500. **Critical distinction: the distillation step was SFT on reasoning traces, NOT RL at the small model. The RL was applied to the 671B model.** RL at small scale (R1-Zero experiments) showed readable reasoning only emerging above ~7B parameters. Below that, RL training was unstable and outputs were often incoherent. |
| **ORPO — "Monolithic Preference Optimization without Reference Model"** (Hong, Lee, Thorne, 2024; arXiv:2403.07691) | Combines SFT and preference alignment into a single training step using odds ratio penalty. No reference model needed. Fine-tuning Phi-2 (2.7B) and Mistral (7B) on UltraFeedback achieves 12.20% AlpacaEval 2.0, 66.19% IFEval, 7.32 MT-Bench. **Tested at 2.7B scale — relevant scale for our use case. But all benchmarks measure instruction-following quality, NOT domain factual recall.** |
| **ΨPO / IPO / KTO — "A General Theoretical Paradigm to Understand Learning from Human Preferences"** (Azar et al., 2023; arXiv:2310.12036) | Derives a general objective ΨPO that encompasses RLHF and DPO as special cases. Shows DPO relies on a questionable approximation (substituting pairwise preferences with pointwise rewards). IPO (Identity Preference Optimization) adds regularization to prevent overfitting. **Key theoretical insight: preference optimization methods optimize for relative quality between outputs, NOT absolute factual correctness. The model learns "this answer is better than that answer," not "this fact is true."** |
| **KTO — Kahneman-Tversky Optimization** (Ethayarajh et al., 2024; arXiv:2402.01306) | Only needs binary feedback (good/bad), not paired preferences. Works from 1B to 30B parameters. Matches DPO performance with simpler data requirements. Based on prospect theory (loss aversion). **The binary signal aspect is attractive for maritime data where "is this answer correct?" is easier to label than "which of two answers is better?" But KTO still doesn't ADD knowledge — it only shapes existing outputs.** |
| **SimPO — "Simple Preference Optimization with a Reference-Free Reward"** (Meng, Xia, Chen, 2024; arXiv:2405.14734; NeurIPS 2024) | Uses average log probability as implicit reward, eliminating reference model. More compute and memory efficient than DPO. Outperforms DPO by up to 6.4 points on AlpacaEval 2, 7.5 points on Arena-Hard. Top model on Gemma-2-9B-it ranks #1 on Chatbot Arena among <10B models. **All improvements are in chat quality and instruction following. No evidence of improved factual recall.** |
| **SPIN — "Self-Play Fine-Tuning Converts Weak Language Models to Strong Language Models"** (Chen et al., 2024; arXiv:2401.01335; ICML 2024) | Self-play mechanism: LLM generates training data from previous iterations, then learns to distinguish its own outputs from human-written ground truth. Progressively improves without additional human annotation. Outperforms DPO supplemented with GPT-4 preference data on HuggingFace Open LLM Leaderboard. **Theoretically appealing: converges when model distribution matches target (human) distribution. But for maritime domain, the "human distribution" must contain maritime knowledge — requiring high-quality ground truth data that already encodes the domain.** |
| **Self-Rewarding Language Models** (Yuan et al., 2024; arXiv:2401.10020; ICML 2024) | Model acts as its own judge via LLM-as-a-Judge prompting during iterative DPO training. Both instruction-following AND reward-judging ability improve simultaneously. Llama 2 70B surpasses GPT-4 0613 on AlpacaEval. **Only demonstrated at 70B. A 1.5B model cannot reliably self-judge domain-specific answers it doesn't have the knowledge to evaluate. Self-rewarding requires the model to already KNOW the right answer.** |
| **Smaug / DPO-Positive (DPOP)** (Pal et al., 2024; arXiv:2402.13228) | Shows standard DPO can *reduce* the likelihood of preferred examples while still increasing relative preference. DPOP adds explicit loss term to maintain likelihood of preferred responses. Smaug-72B first open model to surpass 80% on HuggingFace Open LLM Leaderboard. **Important cautionary finding: DPO can actively DEGRADE the model's ability to produce good answers while achieving its optimization objective. This is a real risk for factual accuracy in small models.** |
| **Qwen3 Technical Report** (Qwen Team, 2025; arXiv:2505.09388) | 36T tokens pretraining. Post-training uses four-stage pipeline: (1) Long-CoT Cold Start SFT, (2) RL with rule-based rewards on reasoning tasks, (3) Thinking Mode Fusion SFT, (4) General RL. **The RL stages used verifiable rewards (math, code) and model-based rewards (general). Key: RL was applied to 32B+ models with massive compute. Smaller models (0.6B, 1.7B) were trained via strong-to-weak distillation, NOT direct RL.** This implies Qwen's own team believes direct RL at <3B scale is not effective. |
| **HuggingFace Preference Tuning Blog** (Rasul et al., Jan 2024) | Empirical comparison of DPO, IPO, KTO on 7B models. Finding: DPO > KTO > IPO on MT-Bench with optimal hyperparameters. β = 0.01 works best across methods. **Critical finding: "DPO can achieve the highest MT Bench score" but improvements are in categories like Writing, Roleplay, Humanities — NOT in factual accuracy (Reasoning, Math, Coding showed "large area for improvement").** |
| **HuggingFace DPO-TRL Blog** (Rasul et al., Aug 2023) | Practical guide to DPO with TRL on Llama 2 7B using Stack Exchange data. DPO replaces steps 3-4 of RLHF (reward modeling + RL optimization) with simple classification loss. Works with QLoRA for memory efficiency. **Demonstrates DPO is practical and cheap, but the application was general Q&A quality, not domain-specific knowledge.** |

---

## THE FUNDAMENTAL QUESTION THIS EVALUATION MUST ANSWER

**Do RL/preference optimization methods help a 1.5B model REMEMBER and ACCURATELY RECALL maritime domain knowledge? Or do they only improve style, safety, formatting, and consistency?**

### The Unambiguous Answer: They Primarily Improve Style, Not Knowledge

Here is why, grounded in what these methods actually optimize:

**What every RL/preference method optimizes:**

$$\max_{\pi_\theta} \mathbb{E}_{x \sim D, y \sim \pi_\theta(\cdot|x)} \left[ R(x, y) \right] - \beta \cdot D_{KL}\left(\pi_\theta \| \pi_{ref}\right)$$

This objective says: *maximize reward while staying close to the reference model*. The reward $R(x, y)$ is defined by:
- **DPO/SimPO/ORPO:** Preference pairs — "this answer is better than that one"
- **GRPO:** Group scores — "among N answers, which are best"  
- **KTO:** Binary labels — "this answer is good/bad"
- **RLVR:** Programmatic checks — "does this answer pass verification"
- **SPIN:** Discriminability — "is this from the model or from human?"

**None of these reward signals say: "this fact is true" or "inject this knowledge into your weights."**

The KL constraint ($D_{KL}$) actively PREVENTS the model from drifting far from its reference policy. This KL penalty is a FEATURE for alignment (prevents degeneration) but a LIMITATION for knowledge injection — it explicitly constrains how much the model's internals can change; it cannot learn radically new information.

**The knowledge bottleneck in RL methods:**

```
┌─────────────────────────────────────────────────────────┐
│               KNOWLEDGE FLOW DIAGRAM                     │
│                                                          │
│  PRETRAINING (trillions of tokens)                       │
│       │                                                  │
│       ▼                                                  │
│  [BASE MODEL WEIGHTS] ← This is where knowledge lives   │
│       │                                                  │
│       ▼                                                  │
│  CPT (domain text)                                       │
│       │    ← Knowledge CAN be injected here              │
│       ▼                                                  │
│  SFT (Q&A pairs)                                         │
│       │    ← Knowledge CAN be injected here (limitedly)  │
│       ▼                                                  │
│  RL/Preference (DPO/GRPO/KTO/etc.)                       │
│       │    ← Knowledge CANNOT be injected here           │
│       │    ← Only reshapes how existing knowledge is     │
│       │      surfaced and formatted                      │
│       ▼                                                  │
│  [ALIGNED MODEL]                                         │
│  Same knowledge, better presentation                     │
└─────────────────────────────────────────────────────────┘
```

**Concrete maritime example:**

Q: "What is the minimum CO2 concentration limit for enclosed space entry per IMO?"

- **Model without maritime knowledge (base Qwen-1.7B):** May guess wrong (e.g., 0.3%)
- **Same model after DPO/GRPO alignment:** Will phrase the wrong answer more confidently and fluently. "Based on IMO guidelines, the CO2 concentration limit for enclosed space entry is 0.3%." — WRONG, but well-formatted.
- **Model after CPT on maritime text (then DPO):** May recall the correct value (0.5% / 5000 ppm) if it was in the CPT corpus, AND present it cleanly.

**The RL method polishes the presentation of existing knowledge. It cannot create knowledge that doesn't exist in the weights.**

### The One Exception: RLVR (RL from Verifiable Rewards)

RLVR is the most interesting method for factual accuracy because the reward signal IS factual correctness:

```python
def maritime_verification_reward(question, answer):
    """Example RLVR reward for maritime domain"""
    if question_type == "factual_recall":
        # Check if answer contains the correct value
        if "0.5%" in answer or "5000 ppm" in answer:
            return 1.0  # Correct
        else:
            return 0.0  # Incorrect
    elif question_type == "procedural":
        # Check if answer contains required steps in order
        required_steps = ["ventilate", "test atmosphere", "entry permit"]
        if all(step in answer.lower() for step in required_steps):
            return 1.0
        else:
            return 0.0
```

**BUT** — and this is critical — RLVR can only reinforce facts the model ALREADY KNOWS. If the model's weights don't encode "0.5%" as the CO2 limit, RLVR rewards of 0.0 on every generated answer will not cause the model to discover the correct answer. RLVR is like grading a student's exam — it tells them they're wrong, but doesn't teach them the right answer. The model needs to occasionally generate the correct answer (by chance or partial knowledge) for RLVR to reinforce it.

**RLVR works for math** because an RL-trained model can "discover" correct mathematical derivations through random exploration — mathematical truths are derivable from axioms already in the weights. **RLVR fails for maritime facts** because factual knowledge (specific IMO regulation numbers, SOLAS chapter references, equipment specifications) is NOT derivable from axioms — it must be learned from training data.

---

## INDIVIDUAL METHOD ANALYSIS FOR MARITIME CHATBOT

### DPO (Direct Preference Optimization)
**Best for:** Answer quality, reducing verbosity, preferring correct format
**Maritime applicability:** Can train on pairs of (correct maritime answer, incorrect/unsafe maritime answer). Useful for preferring precise answers over vague ones. Works at 1-3B scale. Well-supported in TRL.
**Limitation:** Smaug paper (arXiv:2402.13228) shows DPO can reduce likelihood of preferred outputs. Need DPOP modification or careful β tuning (β=0.01 per HuggingFace experiments).
**Verdict for this use case:** 6/10 — Solid finishing layer. Will NOT add knowledge but will make the chatbot prefer correct answers when it has the knowledge.

### GRPO (Group Relative Policy Optimization)
**Best for:** Reasoning tasks with verifiable answers (math, code)
**Maritime applicability:** Could work for maritime questions with objectively verifiable answers. Generate N answers to "What are the MARPOL annexes?", score them against ground truth, reinforce the best. 50% less VRAM than PPO — feasible on consumer GPU.
**Limitation:** Requires verifiable reward signals. Most maritime knowledge is not cleanly verifiable programmatically. The model needs to generate at least some correct answers in its N samples for GRPO to work — if it NEVER generates the right CO2 limit, GRPO learns nothing.
**Critical evidence:** DeepSeek-R1-Zero (pure RL from scratch) showed readable reasoning only emerged at large scale. At small scale, RL training was unstable and outputs were incoherent. Qwen3 chose strong-to-weak distillation for models <3B rather than direct RL.
**Verdict for this use case:** 5/10 — Theoretically elegant but requires infrastructure (verifiable rewards) that doesn't exist for maritime domain. GRPO at <3B scale is unproven.

### ORPO (Odds Ratio Preference Optimization)
**Best for:** Combining SFT and alignment in one step, saving training time
**Maritime applicability:** Could merge the SFT and alignment steps. Train on maritime Q&A with preference signal simultaneously. Tested at 2.7B (Phi-2) — relevant scale.
**Limitation:** "Monolithic" approach means you get one shot. If the combined SFT+alignment doesn't work, you can't debug which component failed. Standard SFT → DPO pipeline is more controllable.
**Verdict for this use case:** 5/10 — Time-saver but risky at small scale. Better to separate SFT and alignment for debuggability.

### RLVR (RL from Verifiable Rewards)
**Best for:** Tasks with programmatically checkable answers (math, code, factual recall with known answers)
**Maritime applicability:** The MOST promising RL method for maritime accuracy. Can build verifiers for: exact regulation numbers, correct procedure sequences, safety thresholds, equipment specifications. But requires creating a verification corpus — essentially a ground-truth database.
**Limitation:** If you have a ground-truth database of all maritime facts, you could arguably just fine-tune on it directly (SFT) rather than using RL. RLVR adds complexity over SFT for the same knowledge source. The advantage of RLVR over SFT is that it trains the model to be ROBUST to question reformulation — it must produce the correct answer regardless of how the question is phrased.
**Verdict for this use case:** 6/10 — Most promising for factual precision, but the verification infrastructure is expensive to build and may not add much over well-designed SFT.

### KTO (Kahneman-Tversky Optimization)
**Best for:** Scenarios where paired preference data is expensive but binary labels are cheap
**Maritime applicability:** Maritime experts can easily label answers as "correct" or "incorrect" — much easier than comparing two answers. KTO works from 1B to 30B (proven range). Could enable continuous improvement from user feedback thumbs-up/thumbs-down.
**Limitation:** Binary signal is weaker than paired preferences. HuggingFace experiments showed KTO underperforms DPO in paired settings. At 1.5B scale, the weaker signal may be insufficient.
**Verdict for this use case:** 5/10 — Practical for data collection (get maritime experts to rate answers), but weaker signal at small scale.

### SimPO (Simple Preference Optimization)
**Best for:** Compute-efficient preference optimization (no reference model needed)
**Maritime applicability:** Lower memory requirement (no reference model in GPU memory) — critical for training on consumer hardware. Reported as consistently outperforming DPO. Works with Gemma-2-9B, Llama 3, Mistral.
**Limitation:** Not tested below 7B. The average log probability reward may behave differently at 1.5B scale where probability distributions are less well-calibrated. NeurIPS 2024 paper focuses entirely on chat benchmarks, not domain QA.
**Verdict for this use case:** 5/10 — Good efficiency but unproven at small scale, and doesn't address the knowledge gap.

### SPIN (Self-Play Fine-Tuning)
**Best for:** Progressively improving without new data, closing the gap to ground truth
**Maritime applicability:** If ground truth is high-quality maritime Q&A written by experts, SPIN iteratively trains the model to produce answers indistinguishable from expert answers. Requires NO additional annotation beyond the initial ground truth dataset.
**Limitation:** The "self-play" converges when the model perfectly mimics the ground truth distribution. But a 1.5B model may NEVER be able to perfectly replicate expert maritime answers — it lacks the parametric capacity. SPIN would converge at a suboptimal point.
**Critical insight:** SPIN requires the ground truth to contain the knowledge. It's essentially multi-round SFT with a clever training objective. The knowledge still comes from the SFT data, not from the RL mechanism.
**Verdict for this use case:** 4/10 — Iterative improvement is nice but fundamentally limited by data quality and model capacity. Marginal benefit over standard SFT for knowledge tasks.

---

## CRITERION-BY-CRITERION EVALUATION

### 1. Knowledge Retention — Score: 2/10

**The core question:** Do RL/preference methods help the model store and retrieve maritime facts?

**Answer: No. Categorically, demonstrably, fundamentally no.**

**Evidence:**

- **Every RL/preference method is constrained by a KL divergence penalty** that explicitly limits how far the model can drift from its reference/base policy. This is by design — preventing reward hacking and maintaining output coherence. But it also means the model CANNOT learn substantially new information. The KL constraint typically keeps the model within a narrow neighborhood of its starting weights.

- **DPO's theoretical basis (Rafailov et al., 2023) explicitly derives its loss as a reparameterization of the RLHF objective.** The optimal policy under this objective is $\pi^*(y|x) \propto \pi_{ref}(y|x) \cdot \exp(R(x,y)/\beta)$. This says the optimal policy is the reference policy REWEIGHTED by the reward. It does not ADD new outputs the reference model cannot produce — it only changes the PROBABILITY of outputs the reference model already assigns non-zero probability to.

- **If the base model assigns probability ~0 to the correct maritime fact, no amount of preference optimization can surface it.** DPO/GRPO/KTO can only amplify signals that already exist in the model's probability distribution. A 1.5B model that has never seen MARPOL Annex VI content during pretraining cannot be DPO'd into knowing what Annex VI covers.

- **The Smaug/DPOP paper (arXiv:2402.13228) demonstrates that DPO can actually REDUCE the likelihood of correct (preferred) responses.** The standard DPO loss optimizes relative probability: it can satisfy the objective by pushing the rejected probability down faster than the preferred probability falls. This means DPO not only fails to inject knowledge — it can actively DEGRADE existing knowledge.

- **HuggingFace's empirical comparison (blog/pref-tuning) shows the biggest improvements from DPO/KTO/IPO are in Writing, Roleplay, and Humanities — NOT in factual STEM/Reasoning categories.** Their own data shows "a large area for improvement" in Reasoning, Coding, and Math even after preference tuning. Factual knowledge is not what these methods optimize.

**What RL methods DO retain:**
- Whatever knowledge was already in the base model from pretraining
- Whatever knowledge was injected via CPT/SFT before the RL step
- All of this is retained (and possibly slightly degraded due to Smaug-identified failure mode)

**What RL methods DO NOT retain (because they never had it):**
- New domain-specific facts
- Exact numbers, regulation references, procedural steps not in pretraining data
- Maritime-specific knowledge that wasn't in the model before RL training

**Score justification:** 2/10 — RL methods are essentially orthogonal to knowledge retention. They reshape how existing knowledge is presented, not what knowledge exists. The 2 points (rather than 0) acknowledge that RLVR could theoretically reinforce correct factual associations the model partially knows, and that SPIN's ground truth mechanism loosely injects knowledge through its SFT-like component.

---

### 2. Inference Cost — Score: 9/10

**The question:** After RL training, does the model cost more to run on a phone?

**Answer: No. RL methods do not change the model architecture or size.**

**Evidence:**

- **All preference/RL methods produce a model with identical architecture and parameter count to the input model.** DPO on a 1.5B model produces a 1.5B model. GRPO on a 1.5B model produces a 1.5B model. There is zero inference overhead.

- **No additional models needed at inference time.** Unlike RLHF (which sometimes needs the reward model at inference for guided generation), DPO/GRPO/KTO/SimPO/ORPO produce standalone models. The reference model, reward model, and critic are only needed during training.

- **Quantization is unaffected.** The RL'd model quantizes the same way as the base model. GGUF Q4_K_M compression works identically. Mobile deployment via llama.cpp/MLC-LLM is unchanged.

- **One caveat: reasoning-focused RL (GRPO/R1-style) may produce models that generate LONGER outputs** due to chain-of-thought reasoning traces. If the model learns to "think aloud" (like DeepSeek-R1-Distill), inference takes longer not because of model size, but because of longer generation. For a mobile chatbot where latency matters, this could be a slight concern.

**Score justification:** 9/10 — Perfect score on model size/architecture, minus 1 point for the potential generation-length increase from reasoning-trained models. For a maritime chatbot that should give concise factual answers, this is a minor concern addressable through training data design.

---

### 3. Training Cost — Score: 7/10

**The question:** How expensive is it to apply RL/preference methods to a 1.5B model?

**Answer: Significantly cheaper than CPT or SFT, with important caveats.**

**Evidence — Method-by-method compute cost:**

| Method | Reference Model? | Reward/Critic Model? | Training Passes | Relative Cost |
|--------|:---:|:---:|:---:|:---:|
| DPO | Yes (frozen) | No | 1 forward+backward | 1.5x SFT |
| SimPO | No | No | 1 forward+backward | ~1x SFT |
| ORPO | No | No | 1 forward+backward | ~1x SFT |
| KTO | Yes (frozen) | No | 1 forward+backward | 1.5x SFT |
| GRPO | Yes (frozen) | No (group scoring) | N generations + 1 update | 3-5x SFT |
| RLVR | Yes (frozen) | Programmatic verifier | N generations + 1 update | 3-5x SFT |
| SPIN | Yes (previous iteration) | No | Multi-round, each ~1x SFT | 3-4x SFT |
| Full RLHF/PPO | Yes (frozen) | Yes (trained separately) | N generations + critic + policy update | 8-15x SFT |

- **DPO on 1.5B model:** ~2-4 hours on a single A100. Uses ~24GB VRAM (model + reference model in memory). Trainable on an RTX 4090 with QLoRA.

- **SimPO/ORPO:** Even cheaper — no reference model means ~12-16GB VRAM for 1.5B model. 1-3 hours on a single A100. The most accessible options.

- **GRPO:** More expensive due to generating N candidate answers per prompt (typically N=8-64). For 10K prompts with N=16 candidates, that's 160K forward passes before the policy update. ~8-12 hours on A100 for 1.5B model. Still feasible on consumer hardware.

- **RLVR:** Similar to GRPO but requires building the verification infrastructure (code for checking maritime answers). The engineering cost exceeds the compute cost.

**The hidden cost: preference data creation.**

All these methods require preference/reward data, which for maritime domain must be created from scratch:

| Data Type | Method | Creation Cost |
|---|---|---|
| Preference pairs (chosen, rejected) | DPO, SimPO, ORPO, SPIN | HIGH — need correct + incorrect maritime answers per question. Requires domain expert review or very careful synthetic generation. 5K-20K pairs needed. |
| Binary labels (good/bad) | KTO | MEDIUM — only need to label individual answers as correct/incorrect. Expert review is simpler. |
| Verifiable rewards | GRPO, RLVR | HIGH engineering cost — need to build programmatic verifiers for maritime facts. Medium ongoing cost. |

**Score justification:** 7/10 — The actual GPU compute is cheap and fast (hours, not days). The cost lies in creating domain-specific preference data, which requires maritime expert involvement. SimPO/ORPO are the most cost-effective in pure compute terms.

---

### 4. Data Efficiency — Score: 6/10

**The question:** How much data do these methods need?

**Answer: They can work with small datasets, but the datasets must be high-quality and domain-specific.**

**Evidence:**

- **DPO on Zephyr:** 66K preference pairs produced the original Zephyr model from Mistral-7B SFT. But this was for general chat — maritime domain would likely need fewer pairs (5K-20K) since the domain is narrower.

- **DPO on NeuralChat (OpenHermes):** 13K preference pairs (GPT-4 chosen, Llama-Chat rejected) produced competitive results. Shows small datasets work for DPO.

- **KTO:** By design requires fewer data points than DPO because binary labels are easier to obtain. KTO paper shows competitive results with same-size datasets and theoretical advantage with unbalanced good/bad ratios.

- **GRPO (DeepSeekMath):** Used ~150K math problems with verifiable answers. For maritime domain, achieving 5K-10K verifiable questions would be ambitious but possible.

- **SPIN:** Uses only the existing SFT dataset — no additional human annotation needed. This is its key advantage. But the quality ceiling is the SFT data quality.

- **DEITA (arXiv:2312.15685):** 6K carefully selected SFT samples matched 60K+ generic samples. Quality >> quantity applies to preference data too.

**Maritime data availability assessment:**

Creating maritime preference data requires:
1. Questions about maritime topics (can be synthetically generated — thousands available)
2. Correct answers (can be extracted from textbooks — available if CPT/SFT were done first)
3. Incorrect/inferior answers (can be generated by the model itself — free)
4. Expert validation (2-5 maritime engineers, part-time for 1-2 weeks)

This is feasible. 5K-10K validated preference pairs is achievable within the project scope.

**Score justification:** 6/10 — Moderate data requirements that are feasible to meet. The bottleneck isn't dataset SIZE but dataset QUALITY — every preference pair must be factually validated by a maritime expert, which is a human-in-the-loop bottleneck. KTO's binary labels lower this barrier significantly.

---

### 5. Accuracy on Domain QA — Score: 3/10

**The core question:** After applying RL/preference methods, will the chatbot answer maritime questions more accurately?

**Answer: Only marginally, and only for knowledge the model already has.**

**Evidence:**

- **RL methods optimize for PREFERENCE, not for TRUTH.** If the preference data says "Answer A is preferred over Answer B," the model learns to produce A-like answers. If A happens to be factually correct and B is wrong, the model learns to prefer correct answers. But the model doesn't learn WHY A is correct — it learns the surface pattern of what A looks like.

- **The HuggingFace preference tuning experiments show minimal improvement in factual categories.** On Zephyr:
  - Writing: significant improvement after DPO
  - Roleplay: significant improvement
  - Reasoning: minimal improvement  
  - Math: minimal improvement
  - STEM: minimal improvement
  
  The pattern is clear: preference optimization improves STYLE categories, not KNOWLEDGE categories.

- **For maritime domain, "accuracy" means exact factual recall:**
  - "What is the flash point of fuel oil under SOLAS?" → 60°C (this is a FACT)
  - "How many lifeboats per side does SOLAS require for a vessel with 200 passengers?" → (requires calculation from SOLAS formula)
  - "List the six annexes of MARPOL" → (requires recall of a specific list)

  RL/preference optimization cannot improve the model's ability to recall these facts unless the model already partly knows them.

- **Where RL CAN help accuracy marginally:**
  - If the model has partially correct knowledge (gets the right answer 40% of the time), RLVR/GRPO can increase the success rate to perhaps 60-75% by reinforcing the correct output pathway
  - DPO can reduce hallucinated "plausible-sounding wrong answers" if trained with preference pairs that punish hallucination
  - GRPO/RLVR can train the model to say "I don't know" rather than hallucinate (by rewarding uncertainty acknowledgment)

**The RLVR special case:**

RLVR with maritime-specific verifiers is the ONE scenario where accuracy could meaningfully improve:
- If a verifier checks "does the answer contain '60°C' for the flash point question?" 
- And the model sometimes generates "60°C" and sometimes generates "52°C"
- RLVR will reinforce the 60°C pathway and suppress the 52°C pathway

But this only works if the model ALREADY sometimes generates the correct value. If the correct value never appears in the model's output distribution, RLVR cannot help.

**Score justification:** 3/10 — Minimal accuracy improvement for domain-specific factual QA. The 3 points acknowledge that RL can slightly improve accuracy for partially-known facts (via RLVR/GRPO), and can reduce hallucination (via DPO preference for honest answers). But the core limitation — RL cannot inject knowledge — makes this a poor approach for improving maritime accuracy.

---

### 6. Mobile Deployability — Score: 9/10

**The question:** Do RL methods affect mobile deployment?

**Answer: No. This is the best aspect of RL methods.**

**Evidence:**

- **Model architecture unchanged.** Same parameter count, same layer structure, same attention mechanism. A 1.5B model after DPO is still a 1.5B model.

- **Quantization compatibility:** RL-trained models quantize identically to SFT-trained models. Q4_K_M, Q5_K_M, Q8_0 — all work the same. No special considerations.

- **No runtime dependencies.** DPO/GRPO/KTO/SimPO produce self-contained models. No reward model, no reference model, no verifier needed at inference. The phone only needs the final model weights.

- **Inference speed:** Token generation speed is unchanged (same architecture, same size). On iPhone 15 with Qwen3-1.7B Q4: ~15-25 tok/s via llama.cpp. RL training doesn't change this.

- **Memory footprint:** Unchanged from the base model. 1.5B Q4 ≈ 1.0-1.2GB RAM. Fits comfortably in 3-6GB mobile RAM budget.

**One concern — reasoning verbosity:**

If GRPO/RL training induces chain-of-thought reasoning (à la DeepSeek-R1), the model may generate longer responses. For a maritime chatbot where users expect concise answers:
- Question: "What is the MARPOL Annex I about?"
- Expected answer: "MARPOL Annex I covers prevention of pollution by oil from ships."
- CoT-trained answer: "Let me think about this... MARPOL stands for Marine Pollution... it has 6 annexes... Annex I deals with... [200 tokens of thinking] ... MARPOL Annex I covers prevention of pollution by oil from ships."

This is solvable by NOT using reasoning-oriented RL training, or by using Qwen3's `enable_thinking=false` mode to suppress CoT.

**Score justification:** 9/10 — Near-perfect mobile deployability. RL methods are transparent to the deployment pipeline. The 1 point deduction is for the CoT verbosity risk, which is avoidable.

---

### 7. Robustness — Score: 5/10

**The question:** Does the RL-aligned model handle edge cases, adversarial inputs, and novel question phrasings better?

**Answer: Somewhat — this is one of RL's genuine strengths, but it comes with caveats at small scale.**

**Evidence for improved robustness:**

- **Alignment is the primary purpose of these methods.** DPO/KTO/GRPO were designed to make models:
  - Refuse harmful queries ("How do I disable the fire alarm?")
  - Handle ambiguous questions gracefully
  - Acknowledge uncertainty ("I'm not confident about this specific regulation")
  - Prefer safe/correct answers over risky/wrong ones

- **GRPO specifically improves robustness to question reformulation** because it generates N answers and reinforces the best — this means the policy learns to be correct regardless of how the question is phrased.

- **DPO with carefully chosen preference pairs can explicitly train for robustness:**
  ```
  Chosen: "I'm not sure about the exact regulation number. The general principle 
           is that enclosed spaces must be ventilated and tested before entry."
  Rejected: "According to SOLAS Chapter XI-2, Regulation 13.4.2, the requirement 
             is exactly 0.3% CO2." [confident but wrong]
  ```
  This teaches the model to prefer honest uncertainty over confident hallucination.

**Evidence against robustness at small scale:**

- **RL training at <3B is notoriously unstable.** DeepSeek-R1-Zero showed that pure RL on small models produced incoherent outputs. Qwen3 used distillation rather than direct RL for their <3B models. The optimization landscape at small scale is too noisy for RL to converge reliably.

- **DPO overfitting is a documented problem.** The HuggingFace experiments showed that DPO quickly overfits on preference datasets, especially with small β values. Overfitted models can be LESS robust than the base model — confidently producing training-data-similar outputs but failing on novel inputs.

- **Limited preference data coverage.** With only 5K-10K maritime preference pairs, the model sees a tiny fraction of possible question phrasings. Robustness to unseen phrasings depends on the model's generalization ability, which is limited at 1.5B.

**Score justification:** 5/10 — RL methods genuinely improve alignment and safety behavior, which is valuable for a maritime safety chatbot. But the robustness gains are modest at small scale due to training instability, overfitting risk, and limited preference data coverage. The model will handle common questions well but may fail unpredictably on unusual formulations.

---

### 8. Catastrophic Forgetting — Score: 7/10

**The question:** Does RL/preference training cause the model to forget previously learned knowledge?

**Answer: Less than CPT or SFT, by design.**

**Evidence:**

- **KL divergence constraint is the built-in safeguard.** Every RL/preference method includes either an explicit KL penalty (DPO, KTO, GRPO) or an implicit one (ORPO, SimPO). This constraint ensures the trained model stays close to the reference/base model in output distribution space. The same feature that prevents knowledge injection also prevents knowledge loss.

- **DPO modifies the model's output distribution less than SFT.** DPO adjusts relative probabilities between preferred and rejected outputs. SFT directly updates the model to maximize probability of specific outputs. DPO's lighter touch means less disruption to existing knowledge.

- **Empirical evidence:** "LoRA Learns Less and Forgets Less" (arXiv:2405.09673) showed that lighter-touch fine-tuning methods preserve more pre-existing knowledge. By analogy, RL methods (lighter than SFT) should forget even less.

- **SimPO and ORPO (no reference model) have slightly higher forgetting risk** because there's no explicit anchor to the original model distribution. But their training is still lighter than full SFT.

**The Smaug caveat:**

The DPOP paper (arXiv:2402.13228) showed that standard DPO can reduce the likelihood of PREFERRED outputs. This means DPO can cause the model to FORGET how to produce good answers while technically satisfying its optimization objective. This is a form of catastrophic forgetting that's unique to DPO and not present in standard SFT.

**Mitigation:** Use DPOP (DPO-Positive) loss instead of standard DPO. Or use SimPO/ORPO which don't have this failure mode. Or ensure careful β tuning (β=0.01 per HuggingFace experiments).

**Score justification:** 7/10 — RL methods generally preserve existing knowledge well due to KL constraints. Better than CPT (4/10 on forgetting) and similar to SFT with LoRA. The 3-point deduction accounts for the Smaug-identified DPO failure mode and the risk of reward hacking at small scale degrading output quality.

---

### 9. Maintenance — Score: 6/10

**The question:** How easy is it to update, retrain, and maintain an RL-aligned maritime chatbot?

**Answer: Good tooling exists, but preference data curation is an ongoing burden.**

**Evidence:**

- **Tooling is mature and accessible:**
  - TRL (HuggingFace): Supports DPO, KTO, ORPO, GRPO, SimPO out of the box
  - Axolotl: Supports DPO, ORPO, KTO
  - LLaMA-Factory: Supports DPO, KTO, ORPO, SimPO
  - OpenRLHF: Supports GRPO, PPO, DPO
  - All support LoRA/QLoRA for parameter-efficient training

- **Training runs are fast:** 2-8 hours per RL training run on consumer GPU. Can iterate quickly.

- **Model updates are straightforward:** When maritime regulations change (e.g., new MARPOL amendments), you need to:
  1. Update the base model's knowledge (via CPT or SFT on new text)
  2. Re-run RL/preference alignment on the updated model
  3. Re-quantize and re-deploy

  Step 2 is quick (~4 hours), but Step 1 is necessary AND is the bottleneck. RL alone cannot inject the new regulation.

- **Preference data maintenance is ongoing:**
  - New questions arise as users interact with the chatbot
  - Expert review of model outputs must be continuous
  - Preference datasets need updating as domain standards evolve
  - This is a human-in-the-loop process that doesn't scale effortlessly

- **KTO's advantage:** Binary feedback (thumbs up/down) from users could be collected in production. This creates a natural feedback loop for continuous improvement. This is one of KTO's strongest selling points for a deployed maritime chatbot.

**Score justification:** 6/10 — Mature tooling and fast training make RL methods practical to maintain. But the dependency on preference data curation, expert review, and the need to re-run RL after knowledge updates (CPT/SFT) add maintenance burden. KTO's binary feedback loop is a bright spot. 

---

### 10. Proven at Small Scale (<3B) — Score: 3/10

**The core question:** Have any of these RL methods been proven to improve domain-specific performance on models with 1-3B parameters?

**Answer: Almost no evidence at this scale for domain-specific knowledge tasks.**

**Evidence — what HAS been proven at small scale:**

- **ORPO on Phi-2 (2.7B):** Achieves 12.20% AlpacaEval 2.0, which tests general chat ability, NOT domain knowledge. The result proves ORPO is technically functional at 2.7B, but tells us nothing about maritime knowledge retention.

- **KTO paper claims 1B-30B range:** But the 1B experiments were minimal and focused on general capability benchmarks. No domain-specific evaluation at 1B.

- **DeepSeek-R1-Distill-Qwen-1.5B:** Achieves 83.9% on MATH-500. BUT — this was achieved via SFT distillation of reasoning traces, NOT via direct RL at 1.5B. DeepSeek explicitly chose NOT to apply RL directly to the 1.5B model. They applied RL to the 671B model, generated training data, and SFT'd the small model. This is evidence AGAINST direct RL at small scale.

- **Qwen3-0.6B and Qwen3-1.7B:** The Qwen3 technical report describes a four-stage post-training pipeline (Cold Start SFT → RL → Thinking Mode Fusion SFT → General RL). However, the report explicitly states that smaller models were trained via "strong-to-weak distillation" requiring "only 1/10 GPU hours vs full 4-stage training." This means Qwen's own team found that applying the full RL pipeline directly to small models was less effective than simply distilling from larger RL-trained models.

**Evidence — what has NOT been proven at small scale:**

- **No published work demonstrates RL/preference methods improving factual domain knowledge at <3B.** None.

- **No published work shows GRPO working at <3B for non-mathematical tasks.** DeepSeekMath was 7B. GRPO's group scoring requires the model to generate diverse, sometimes-correct answers — this diversity and partial correctness is harder to achieve at 1.5B.

- **No published work shows DPO improving domain-specific QA accuracy at <3B.** All DPO evaluations at small scale focus on general chat metrics (MT-Bench, AlpacaEval).

- **DeepSeek-R1-Zero (pure RL) experiments showed unstable, incoherent outputs at small scale.** The paper describes that readable reasoning only emerged at large scale. Below ~7B, RL from scratch was not viable.

**The inference from industry behavior:**

Both DeepSeek and Qwen — the two most successful open-weight RL practitioners — chose to NOT apply direct RL to their smallest models (<3B). They instead used distillation (SFT from RL-trained teacher outputs). This is the strongest signal that direct RL at small scale is not effective for these teams' use cases.

**Score justification:** 3/10 — Critically unproven at <3B scale for domain-specific knowledge tasks. The evidence from DeepSeek and Qwen actively suggests that direct RL at this scale is inferior to distillation. The 3 points acknowledge that ORPO has been technically demonstrated at 2.7B (Phi-2) and that the basic DPO/KTO algorithms function at small scale for general alignment.

---

## FINAL SCORING SUMMARY

| Criterion | Score | Weight | Rationale |
|---|:---:|:---:|---|
| 1. Knowledge Retention | 2/10 | Critical | RL cannot inject knowledge. Reshapes existing knowledge only. KL constraint explicitly prevents large weight changes. |
| 2. Inference Cost | 9/10 | Important | Zero inference overhead. Same model size, same speed, no additional models needed at runtime. |
| 3. Training Cost | 7/10 | Moderate | GPU compute is cheap (hours). Data creation is the real cost (expert preference curation). |
| 4. Data Efficiency | 6/10 | Moderate | 5K-10K preference pairs sufficient. KTO needs only binary labels. SPIN reuses SFT data. |
| 5. Accuracy on Domain QA | 3/10 | Critical | Marginal accuracy improvement. Cannot fix unknown facts. RLVR is the only hope for factual precision. |
| 6. Mobile Deployability | 9/10 | Important | Perfect — no model changes, same quantization, same deployment pipeline. |
| 7. Robustness | 5/10 | Important | Improves alignment/safety. Limited by training instability and overfitting at small scale. |
| 8. Catastrophic Forgetting | 7/10 | Important | KL constraints protect existing knowledge. Smaug-identified DPO failure mode is mitigable. |
| 9. Maintenance | 6/10 | Moderate | Good tooling. Preference data curation is ongoing cost. KTO's binary feedback enables production loop. |
| 10. Proven at Small Scale | 3/10 | Critical | Almost no evidence at <3B for domain knowledge. DeepSeek and Qwen chose distillation over direct RL for small models. |

---

## TOTAL SCORE: 57/100

---

## KEY STRENGTHS (3)

### Strength 1: Zero Inference Overhead — The Perfect Finishing Layer
RL/preference methods produce a model with exactly the same architecture, size, and inference cost as the input model. For a mobile deployment where every MB and every millisecond matters, this is ideal. You apply RL once during training, and the model runs on the phone exactly as before — but with better-aligned outputs. No reward model, no reference model, no verifier needed at inference time. This makes RL methods the cheapest possible improvement in the deployment pipeline — pure upside if the base model already has domain knowledge.

### Strength 2: Hallucination Reduction via Preference Alignment
For a maritime safety chatbot, the worst failure mode is confident hallucination — the model authoritatively states a wrong safety threshold. DPO/KTO can be specifically trained to prefer "I'm not confident about this specific value" over "The exact value is X" when X is wrong. By constructing preference pairs that penalize confident-but-wrong answers and reward honest uncertainty, RL methods can make the chatbot SAFER even without adding domain knowledge. This is a genuine, unique value-add that no other training stage (CPT, SFT) specifically addresses.

### Strength 3: Production Feedback Loop via KTO's Binary Labels
KTO enables the simplest possible production feedback loop: deploy the chatbot, maritime engineers use it, they click thumbs-up/thumbs-down on answers, collect this data, periodically retrain with KTO. No expert pairwise comparison needed, no complex annotation pipeline. This creates a LIVING chatbot that improves from real-world use. Combined with periodic CPT/SFT updates for new regulations, KTO provides the continuous improvement mechanism that makes the chatbot maintainable long-term. No other training paradigm provides this as naturally.

---

## KEY WEAKNESSES (3)

### Weakness 1: Fundamental Inability to Inject Domain Knowledge
This is not a flaw in the methods — it is their nature. RL/preference optimization methods optimize HOW the model uses its existing knowledge, not WHAT knowledge it has. The mathematical foundation (KL-constrained reward maximization) explicitly prevents large weight changes that would be needed to encode new facts. For a maritime chatbot that needs to know thousands of specific regulations, procedures, and values, this is a fatal limitation when used as the primary training method. RL methods must come AFTER knowledge injection (CPT + SFT), not instead of it.

### Weakness 2: Critically Unproven at <3B Scale for Domain Tasks  
The world's most capable RL practitioners (DeepSeek, Qwen/Alibaba) both chose not to apply direct RL to their <3B models, instead preferring distillation from RL-trained teachers. DeepSeek-R1-Zero showed incoherent outputs at small scale. No published work demonstrates RL improving domain-specific knowledge accuracy at <3B. This isn't a gap in the literature — it's a signal from practitioners with the most experience. Direct RL at 1.5B for maritime QA is an experiment with no positive precedent to draw from.

### Weakness 3: Preference Data Requires Maritime Domain Expertise
Creating preference data for maritime alignment requires domain experts (licensed marine engineers, surveyors, or senior officers) to validate answers as correct/incorrect. Unlike math (verifiable by computation) or code (verifiable by execution), maritime knowledge verification requires human expertise. "Is this CO2 system testing procedure correct per the latest SOLAS amendments?" cannot be answered by an algorithm — it requires someone who knows the answer. This creates a bottleneck: the quality of RL training is bounded by the availability and reliability of maritime expert reviewers.

---

## VERDICT

**RL/preference methods score 57/100 as a STANDALONE approach — which correctly reflects that they should NEVER be used alone for a knowledge-intensive maritime chatbot.**

They are not a knowledge injection method. They are a quality and alignment layer.

**The car analogy:** RL methods are the paint, polish, and alignment of a car. They make it look professional, handle predictably, and present well. But they do not add an engine, transmission, or fuel. Trying to build a maritime chatbot using only RL methods is like trying to win a race with a beautifully polished car with no engine. The car looks great but goes nowhere.

**The correct role of RL methods:** Step 4 in a 5-step pipeline, applied AFTER the model already has domain knowledge:

1. **CPT** → Inject domain knowledge (the engine)
2. **SFT** → Teach question-answering format (the transmission)
3. **Reasoning Distillation (optional)** → Teach structured thinking (the navigation system)
4. **RL/Preference Alignment** → Polish outputs, reduce hallucination, align with expert preferences (the paint and tuning)
5. **Quantize & Deploy** → Ship to mobile (the delivery)

**RL methods at Step 4 could boost the OVERALL pipeline score from ~82/100 (CPT+SFT+Distillation) to ~87/100** — a meaningful improvement that justifies the relatively low cost. But without Steps 1-2, RL methods alone deliver ~57/100 — a polished but empty chatbot that sounds authoritative while knowing nothing about ships.

---

## BEST COMBINATION: Recommended RL Method for This Pipeline

Given our specific constraints (1.5B model, maritime domain, mobile deployment, limited expert availability):

```
MOST RECOMMENDED RL METHOD: DPO (or DPOP) + KTO hybrid

Pipeline Integration:
    
    STEP 1: CPT on Maritime Text
        │   (inject domain knowledge into weights)
        ▼
    STEP 2: SFT on Synthetic Maritime Q&A
        │   (teach chatbot behavior)
        ▼
    STEP 3: DPO/DPOP Alignment  ← PRIMARY RL METHOD
        │   
        │   WHY DPO:
        │   • Most proven and stable at close-to-small scale
        │   • Simplest to implement (TRL DPOTrainer, <50 lines of config)
        │   • Best tooling support across all frameworks
        │   • Smaug-identified failure mode fixable via DPOP
        │   • Works with LoRA (since we're adjusting style, not knowledge)
        │   
        │   PREFERENCE DATA:
        │   • 5K-10K maritime Q&A pairs
        │   • Chosen: Expert-validated correct answers from SFT model
        │   • Rejected: Model-generated incorrect/vague/hallucinated answers
        │   • Special pairs for hallucination reduction:
        │     Chosen: "I'm not certain about the exact regulation."
        │     Rejected: "The regulation states..." [wrong value]
        │   
        │   TRAINING:
        │   • β = 0.01 (per HuggingFace experiments)
        │   • 1 epoch max (to prevent overfitting)
        │   • LoRA r=16, α=32 (sufficient for alignment)
        │   • ~2-4 hours on single A100 / ~6-8 hours on RTX 4090
        ▼
    STEP 4: KTO Production Alignment  ← ONGOING RL METHOD
        │   
        │   WHY KTO (in production):
        │   • Enables continuous improvement from user feedback
        │   • Maritime engineers click 👍/👎 on chatbot answers
        │   • Collect 1K-5K binary-labeled examples over weeks of use
        │   • Periodically retrain (monthly) with accumulated feedback
        │   • No expert comparison needed — just "was this helpful?"
        │   
        │   This creates a VIRTUOUS CYCLE:
        │   Deploy → Collect feedback → Retrain → Redeploy → Better feedback
        │
        ▼
    STEP 5: Quantize to Q4_K_M → Deploy on Mobile
```

**Methods NOT recommended for this use case:**

| Method | Why Not |
|---|---|
| GRPO | Requires verifiable rewards infrastructure; unproven at <3B; DeepSeek chose distillation for small models |
| RLVR | Powerful concept but engineering-heavy; building maritime verifiers is a major project; same knowledge from verifier database could be used for SFT more simply |
| ORPO | Merges SFT and alignment — loses debuggability; better to keep stages separate for a novel domain application |
| SimPO | Unproven below 7B; average log probability reward may be poorly calibrated at 1.5B |
| SPIN | Marginal improvement over standard SFT; adds complexity without clear domain knowledge benefit |
| Full RLHF/PPO | Too expensive, too unstable; GRPO/DPO dominate PPO in all relevant metrics |

**Expected improvement from adding DPO+KTO to the pipeline:**

| Metric | CPT + SFT Only | CPT + SFT + DPO + KTO |
|---|---|---|
| Answer factual accuracy | 70-75% | 72-78% (modest improvement) |
| Answer formatting quality | 60-70% | 85-90% (major improvement) |
| Hallucination rate | 15-25% | 8-15% (significant reduction) |
| Uncertainty calibration | Poor | Moderate (model learns to say "I don't know") |
| User satisfaction | 65-75% | 80-88% (DPO+KTO polish matters for UX) |
| Safety (refuses dangerous advice) | 50-60% | 85-95% (core purpose of alignment) |

**Bottom line:** RL methods are the cheapest, fastest, most deployment-friendly way to turn a knowledgeable-but-rough maritime chatbot into a professional, safe, well-calibrated product. They are not the foundation — they are the finishing layer. Skip them and you have a capable but rough prototype. Include them and you have a producible product. But never mistake the finishing layer for the foundation.
