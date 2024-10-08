# transfromers version 4.32.0
import warnings

warnings.filterwarnings("ignore")

import gemma_self_extend_patch as GemmaSE
from modify_utils import modify_method_of_instance
from functools import partial
import json
from transformers.models.gemma.modeling_gemma import GemmaAttention
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

original_gemma_forward = GemmaAttention.forward
self_extend_forward = partial(
    GemmaSE.self_extend_forward, group_size_1=16, group_size_2=2048
)

device = "cpu"  # or "cuda" if you use a GPU, "mps" for Apple Silicon
model_path = "google/gemma-2-2b-it"  # gated model, need hf token
model = AutoModelForCausalLM.from_pretrained(
    model_path,
    torch_dtype=torch.bfloat16,  # prevent upcasting to save RAM
).to(device)
tokenizer = AutoTokenizer.from_pretrained(model_path)
model.eval()


for line in open("passkey_examples_10k.jsonl", "r"):
    example = json.loads(line)
    prompt_postfix = "What is the pass key? The pass key is "
    prompt = example["input"] + prompt_postfix
    input_ids = tokenizer(prompt, return_tensors="pt").input_ids.to(device)
    print("-----------------------------------")
    print(f"#Tokens of Prompt:", input_ids.shape[1], end=" ")
    print("Passkey target:", example["target"])

    modify_method_of_instance(
        model, "GemmaAttention", "forward", original_gemma_forward
    )
    tokens = model.generate(input_ids, max_new_tokens=6)
    answer = (
        "Gemma:     ["
        + prompt_postfix
        + tokenizer.decode(
            tokens[0].tolist()[input_ids.shape[1] :], skip_special_tokens=True
        )
        + "]"
    )
    answer = answer.replace("\n", "\\n")
    print(answer)

    modify_method_of_instance(model, "GemmaAttention", "forward", self_extend_forward)
    tokens = model.generate(input_ids, max_new_tokens=6)
    answer = (
        "SelfExtend: ["
        + prompt_postfix
        + tokenizer.decode(
            tokens[0].tolist()[input_ids.shape[1] :], skip_special_tokens=True
        )
        + "]"
    )
    answer = answer.replace("\n", "\\n")
    print(answer)
    print("-----------------------------------\n")

modify_method_of_instance(model, "GemmaAttention", "forward", self_extend_forward)
model.save_pretrained("SelfExtend")
