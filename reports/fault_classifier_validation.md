# SkyGuard Phase 5 artifact validation

> Historical artifact validation only. Passing this integrity check does not make the Phase 5 input contract SIH-compliant. The deployed result is Phase 10.

**Status: PASS**

- Errors: 0
- Policy frozen using 2023: True
- Classifier features: 68
- Absolute calendar shortcuts excluded: True

| Test | Phase 4 best F1 | Phase 5 F1 | Absolute gain |
|---|---:|---:|---:|
| time_test | 0.1814 | 0.5247 | +0.3433 |
| station_test | 0.2274 | 0.5641 | +0.3367 |

| Split | Rows | Expected | Checksum |
|---|---:|---:|---|
| validation | 181,308 | 181,308 | `ceb3cd46be5d7d4ed6e46fe8caf0e4911042594d8c77f2835c2ffa04ad53842e` |
| time_test | 182,053 | 182,053 | `a230878e77fc855cb86033e22de14b12c79c242af511a01ef688410f28aea094` |
| station_test | 10,491 | 10,491 | `c50ee4e40511b99b1f12bbd48edee9ea1b89a2f550fee8ca6eb30526706bd8db` |
