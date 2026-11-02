# LAION Aesthetics V1: bundled ViT-B/32 head

MIT licensed, copyright 2022 LAION AI; see [LICENSE](LICENSE).

- Upstream: https://github.com/LAION-AI/aesthetic-predictor
- Pinned commit: `6d122adad522ab246644d9dc1c6d7a3810ee255f`
- Original: `sa_0_4_vit_b_32_linear.pth`
- Original SHA-256: `c7b14cead230694acc7b9447974d3cad78003c72da032e402a303b6c2429e85f`
- Packaged JSON SHA-256: `fbd3047102bc48da26afb272a215a7db3b872c5d5c511972d4c5ee44b4863ef2`

The JSON contains the original float32 linear weights and bias, converted once using
`torch.load(path, map_location="cpu", weights_only=True)`, then `.view(-1).tolist()` and
`.item()`. Runtime uses NumPy; PyTorch and network downloads are unnecessary. The provider
checks the packaged checksum. The golden regression compares NumPy with the original
PyTorch linear operation on a normalized deterministic sinusoidal vector (3.690062999725342).

## Encoder compatibility

The original head requires L2-normalized **OpenAI CLIP ViT-B/32** projected image vectors (512).
[Qdrant's model card](https://huggingface.co/Qdrant/clip-ViT-B-32-vision) identifies its ONNX
model as a port of sentence-transformers/clip-ViT-B-32. That model's
[config](https://huggingface.co/sentence-transformers/clip-ViT-B-32/blob/main/0_CLIPModel/config.json)
identifies `openai/clip-vit-base-patch32`, with projection dimension 512. The adapter exposes
this explicit space identifier; the head refuses other spaces even if dimensions match.
SigLIP vectors are never passed to this head. SigLIP jobs use the separately bundled CLIP
image tower, reusing or populating its own file cache.

## Meaning and limits

[Upstream documentation](https://github.com/LAION-AI/laion-datasets/blob/main/laion-aesthetic.md)
describes 4,000 annotations on a 0–10 visual-appeal scale. Inference is an unconstrained
linear prediction; the app clips `prediction / 10` to [0,1] for a component bar. It is not a
probability, engagement model, universal beauty measurement or a professional photo-quality
benchmark. Training preferences and dataset bias can differ from this photographer's taste.

The signal contributes 30% of the optional Social Media overlay; that overlay's influence
is user-controlled. These blend weights are product heuristics, not published optimal weights.
CLIP jobs reuse every technically viable photo's existing vector. Other encoders evaluate
up to 256 technically viable photos ranked by baseline quality, with a visible warning if
limited. Unevaluated photos keep their ordinary scores; no learned score is invented.
Cache keys include the original file size/mtime and the packaged model version/checksum.
