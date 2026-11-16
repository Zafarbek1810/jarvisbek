"""Safetensors -> whisper.cpp GGML, without PyTorch or downloaded Python code.

Tensor layout follows ggml-org/whisper.cpp/models/convert-h5-to-ggml.py (MIT).
Usage: python convert-uzbek-whisper.py MODEL_DIR OUTPUT.bin
MODEL_DIR needs model.safetensors, config.json, vocab.json, mel_filters.npz.
Optional setup dependency: pip install safetensors
"""
import json
import struct
import sys
from pathlib import Path

import numpy as np
from safetensors.numpy import load_file

MAPPING = {
 'self_attn.k_proj':'attn.key', 'self_attn.q_proj':'attn.query',
 'self_attn.v_proj':'attn.value', 'self_attn.out_proj':'attn.out',
 'self_attn_layer_norm':'attn_ln', 'encoder_attn.k_proj':'cross_attn.key',
 'encoder_attn.q_proj':'cross_attn.query', 'encoder_attn.v_proj':'cross_attn.value',
 'encoder_attn.out_proj':'cross_attn.out', 'encoder_attn_layer_norm':'cross_attn_ln',
 'fc1':'mlp.0', 'fc2':'mlp.2', 'final_layer_norm':'mlp_ln',
 'encoder.layer_norm.bias':'encoder.ln_post.bias', 'encoder.layer_norm.weight':'encoder.ln_post.weight',
 'encoder.embed_positions.weight':'encoder.positional_embedding',
 'decoder.layer_norm.bias':'decoder.ln.bias', 'decoder.layer_norm.weight':'decoder.ln.weight',
 'decoder.embed_positions.weight':'decoder.positional_embedding',
 'decoder.embed_tokens.weight':'decoder.token_embedding.weight',
}

def byte_decoder():
    values=list(range(33,127))+list(range(161,173))+list(range(174,256))
    chars=values.copy();extra=0
    for value in range(256):
        if value not in values:
            values.append(value);chars.append(256+extra);extra+=1
    return {chr(char):value for value,char in zip(values,chars)}

def convert(root: Path, output: Path):
    cfg=json.loads((root/'config.json').read_text())
    weights=load_file(root/'model.safetensors')
    # Safetensors may omit one of the tied embedding/output tensors.
    if 'model.decoder.embed_tokens.weight' not in weights:
        weights['model.decoder.embed_tokens.weight']=weights['proj_out.weight']
    with output.open('wb') as f:
        def integer(value):f.write(struct.pack('<i',value))
        for value in [0x67676d6c,cfg['vocab_size'],cfg['max_source_positions'],cfg['d_model'],
                      cfg['encoder_attention_heads'],cfg['encoder_layers'],cfg['max_target_positions'],
                      cfg['d_model'],cfg['decoder_attention_heads'],cfg['decoder_layers'],cfg['num_mel_bins'],1]:
            integer(value)
        with np.load(root/'mel_filters.npz',allow_pickle=False) as filters:
            mel=filters[f"mel_{cfg['num_mel_bins']}"]
        integer(mel.shape[0]);integer(mel.shape[1]);f.write(mel.astype('<f4').tobytes())
        tokens=json.loads((root/'vocab.json').read_text());decoder=byte_decoder();integer(len(tokens))
        for token,_ in sorted(tokens.items(),key=lambda item:item[1]):
            data=bytes(decoder[char] for char in token);integer(len(data));f.write(data)
        for source,value in weights.items():
            if source=='proj_out.weight':continue
            parts=source.split('.')[1:]
            if parts[1]=='layers':
                parts[1]='blocks'; name='.'.join(parts[:3]+[MAPPING['.'.join(parts[3:-1])]]+parts[-1:])
            else:
                name='.'.join(parts);name=MAPPING.get(name,name)
            data=value.squeeze()
            if name in ['encoder.conv1.bias','encoder.conv2.bias']:data=data.reshape(-1,1)
            f32=data.ndim<2 or name in ['encoder.conv1.bias','encoder.conv2.bias','encoder.positional_embedding','decoder.positional_embedding']
            data=np.ascontiguousarray(data,dtype='<f4' if f32 else '<f2')
            encoded=name.encode();integer(data.ndim);integer(len(encoded));integer(0 if f32 else 1)
            for dimension in reversed(data.shape):integer(dimension)
            f.write(encoded);f.write(data.tobytes())
    print(f'Converted {len(weights)} tensors: {output} ({output.stat().st_size} bytes)')

if __name__=='__main__':convert(Path(sys.argv[1]),Path(sys.argv[2]))
