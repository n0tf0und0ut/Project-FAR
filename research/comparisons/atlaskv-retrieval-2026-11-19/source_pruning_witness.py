"""CPU micro-reproductions of AtlasKV inference index-space mismatches.

Source: HKUST-KnowComp/AtlasKV @ 61e3abc1fb09fbfb426cfc847c4c26c5e94bcaeb
src/atlaskv/models/llama3_model.py lines 193-217, 518-566.

These are isolated tensor operations *transcribed* from upstream, not a runtime
execution of the full pretrained AtlasKV model or its integrated attention path.
"""
from __future__ import annotations
import json
import torch

UPSTREAM_COMMIT = '61e3abc1fb09fbfb426cfc847c4c26c5e94bcaeb'

def upstream_prune_key(attn_weights, layer_kb_indices=None, topk_size=20):
    assert attn_weights.requires_grad is False
    batch_size, num_heads, max_len, layer_kb_len = attn_weights.shape
    attn_weights_prob = torch.nn.functional.softmax(attn_weights, dim=-1, dtype=torch.float32)
    if layer_kb_indices is not None:
        if topk_size >= layer_kb_len:
            return layer_kb_indices
        with torch.autograd.no_grad():
            top_idx = torch.topk(attn_weights_prob.sum((1, 2)), min(layer_kb_len, topk_size), dim=-1)[1]
        return layer_kb_indices[top_idx.squeeze().to('cpu')]
    else:
        if topk_size >= layer_kb_len:
            return range(layer_kb_len)
        with torch.autograd.no_grad():
            top_idx = torch.topk(attn_weights_prob.sum((1, 2)), min(layer_kb_len, topk_size), dim=-1)[1]
        return top_idx.squeeze().to('cpu')


def reproduce():
    # The current code calculates attention over the filtered inter keys only,
    # then maps its LOCAL winning position using the UNFILTERED global ids.
    global_inter_ids=torch.tensor([10,20,30,40])
    selected_inter_global_positions=torch.tensor([2,3])
    inter_logits=torch.tensor([[[[0.0,9.0]]]])
    actual_inter=int(upstream_prune_key(inter_logits,global_inter_ids,topk_size=1))
    expected_inter=int(upstream_prune_key(inter_logits,global_inter_ids[selected_inter_global_positions],topk_size=1))

    # The leaf attention is computed over selected leaf keys, but the
    # same local top_idx is applied to all global kb_values.
    global_values=torch.arange(10,dtype=torch.float32).view(1,1,10,1)
    selected_leaf_global_positions=torch.tensor([3,7])
    leaf_logits=torch.tensor([[[[0.0,9.0]]]])
    local_leaf_idx=int(upstream_prune_key(leaf_logits,None,topk_size=1))
    actual_value=float(global_values[:,:,local_leaf_idx,:].item())
    expected_value=float(global_values[:,:,selected_leaf_global_positions[local_leaf_idx],:].item())

    # Contrasting positive controls: no pruning and selected-prefix subset.
    unpruned_ids=torch.tensor([10,20])
    positive_inter=int(upstream_prune_key(inter_logits,unpruned_ids,topk_size=1))
    positive_leaf=float(global_values[:,:,1,:].item())
    assert actual_inter==20 and expected_inter==40
    assert actual_value==1 and expected_value==7
    assert positive_inter==20 and positive_leaf==1
    return dict(source_commit=UPSTREAM_COMMIT,scope='isolated upstream indexing expressions; not full AtlasKV inference',
                intermediate=dict(actual_global_id=actual_inter,expected_global_id=expected_inter),
                leaf=dict(actual_value=actual_value,expected_value=expected_value),
                controls={'unpruned_inter_correct':positive_inter==20,'prefix_leaf_correct':positive_leaf==1})

if __name__=='__main__':
    print(json.dumps(reproduce(),sort_keys=True,indent=2))
