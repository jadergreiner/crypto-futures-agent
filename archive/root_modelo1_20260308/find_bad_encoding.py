#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys

with open('scripts/train_ppo_skeleton.py', 'rb') as f:
    content = f.read()

print("Procurando bytes não-ASCII em train_ppo_skeleton.py...")
for i in range(len(content)):
    if content[i] > 127:
        context_start = max(0, i - 20)
        context_end = min(len(content), i + 20)
        context = content[context_start:context_end]
        try:
            context_str = context.decode('utf-8', errors='replace')
        except:
            context_str = str(context)

        print(f"Posicao {i}: byte {hex(content[i])}")
        print(f"  Context: ...{context_str}...")
