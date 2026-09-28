# STABLE ID SCHEME

## Prefixes
| Prefix | Meaning |
|--------|---------|
| SRC-nnn | Source inventory record (from carriers) |
| CAN-GOV-nnn | Governance canonical record |
| CAN-CAR-nnn | Andi Car canonical record |
| CAN-BM-nnn | Benchmark canonical record |
| CAN-BM-Hnnn | Benchmark historical record |
| CAN-EV-nnn | Evidence canonical record |
| CAN-LAB-nnn | Lab canonical record |
| CAN-LAB-Hnnn | Lab historical record |
| HR-nnn | Human Review Register entry |
| VC-nnn | Version chain |
| DUP-nnn | Duplicate analysis entry |
| DEP-nnn | Cross-project dependency |
| SC-nnn | Shared concept |
| SUP-nnn | Supersession record |

## Rules
- IDs are permanent once assigned. Never reuse retired IDs.
- Physical filenames may change; IDs survive moves.
- Each canonical record file includes its stable ID in a machine-readable HTML comment header.
- Sequential numbering within prefix. Collision-resistant within this archive.
