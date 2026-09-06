| fold | va_curve equal (CONST=FLOOR5=FIX7) | alpha_curve equal | argmax(va) | CONST best_ep | FLOOR5 best_ep | FIX7 best_ep | va@CONST | va@FLOOR5 | va@FIX7 | FLOOR5 changed? |
|---|---|---|---|---|---|---|---|---|---|---|
| 202501 | True | True | 6 | 6 | 6 | 7 | -3.109 | -3.109 | -3.905 | False |
| 202502 | True | True | 5 | 5 | 5 | 7 | -3.299 | -3.299 | -3.957 | False |
| 202503 | True | True | 4 | 4 | 6 | 7 | -4.011 | -4.105 | -5.598 | True |
| 202504 | True | True | 2 | 2 | 8 | 7 | -3.783 | -4.579 | -6.221 | True |
| 202505 | True | True | 1 | 1 | 7 | 7 | -3.002 | -4.426 | -4.426 | True |
| 202506 | True | True | 2 | 2 | 5 | 7 | -3.336 | -3.787 | -6.056 | True |
| 202507 | True | True | 2 | 2 | 5 | 7 | -4.327 | -4.474 | -6.375 | True |
| 202508 | True | True | 4 | 4 | 5 | 7 | -3.734 | -3.996 | -4.795 | True |
| 202509 | True | True | 5 | 5 | 5 | 7 | -3.728 | -3.728 | -4.195 | False |
| 202510 | True | True | 5 | 5 | 5 | 7 | -3.817 | -3.817 | -4.158 | False |
| 202511 | True | True | 10 | 10 | 10 | 7 | -4.933 | -4.933 | -5.210 | False |
| 202512 | True | True | 11 | 11 | 11 | 7 | -7.076 | -7.076 | -7.308 | False |
| 202601 | True | True | 12 | 12 | 12 | 7 | -7.870 | -7.870 | -7.984 | False |
| 202602 | True | True | 6 | 6 | 6 | 7 | -7.984 | -7.984 | -8.017 | False |
| 202603 | True | True | 11 | 11 | 11 | 7 | -7.812 | -7.812 | -7.914 | False |
| 202604 | True | True | 3 | 3 | 8 | 7 | -7.430 | -7.482 | -7.603 | True |
| 202605 | True | True | 3 | 3 | 11 | 7 | -6.974 | -6.976 | -7.000 | True |
| 202606 | True | True | 3 | 3 | 7 | 7 | -6.875 | -6.899 | -6.899 | True |
| 202607 | True | True | 7 | 7 | 7 | 7 | -7.061 | -7.061 | -7.061 | False |
| 202608 | True | True | 4 | 4 | 5 | 7 | -6.322 | -6.347 | -6.415 | True |

- all folds: va_curve/alpha_curve identical across CONST/FLOOR5/FIX7 and rules obeyed = **True**; FLOOR5 changed the kept epoch in 10/20 folds ([202503, 202504, 202505, 202506, 202507, 202508, 202604, 202605, 202606, 202608]); CONST best_ep ≤ 2 in 4/20; mean validation-score gap vs CONST: FLOOR5 -0.164, FIX7 -0.731 (bps/anchor, validation slice)
