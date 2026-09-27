> **创建:** 2026-09-27 17:47 UTC | **Session:** acting_lead/research_resume_0927 | **状态:** final（输入边界修复交付，未运行真实首120） | **作废条件:** 新source/test SHA或首120输入合同改变；不替代ms消费者现金控制

# 首120输入门边界修复

接 `../d10_first_span_identity_20260928/README.md`；root独立复审指出off无符号差分溢出和路径TOCTOU。本件仅修独立检查器，不修改旧identity manifest、测试收据、D10 213 pins或funding代理文件。

修前用真实API和小临时NPZ复现4个漏拦断言：uint64 off=[0,4,2,6]导致重复分配、[0,7,6]超实际6行；ledger打开后把路径换成同SHA但另一inode；manifest先验证原SHA、第二次文本读取则给另一个ledger身份。日志BEFORE_RED保留，仅去行尾空白，原始SHA另记。

修复：off逐项转Python int；先显式0≤off≤len(ft)，再直接标量相邻比较，不做固定宽度减法。ledger前后取os.fstat(fd)，比device/inode/size/mtime_ns/ctime_ns，并核路径stat仍对应同一打开文件。通用SHA也用同样FD/路径核查。manifest从一个FD读入一份字节；哈希和JSON解析都使用该份字节，无第二次读取。

13/13小型输入测试通过，无执行器导入、无模拟、无远程大文件重新hash。状态仍只INPUT_CONTRACT_PASS_CASH_UNVALIDATED、execution_ready=false；首120现金/新targets来源等门未扩大或豁免。

- 新checker sourceSHA `5f1ba04e22ac45ae4b7c632a9df1ae11f8f55b164c59ba33e7bc0fc62800c104`（旧 `0d2556e1e322611c221673952ec25175f41256f6bfd1a025a5d36ea10496abee`）。
- 测试SHA `3f20a01fa1c1ff676d2c9e5e77b2a9deb00d5c70ebadb367662b92f9c25d8f4b`。
- 旧identity manifest SHA `9a7de4e6cb0a02b9b8fff94c232635bce6aec8ba15ba06cb2baca3522c920b78` **未改**；旧10/10收据不改绑新代码。
- 本次 `VERIFICATION.json` SHA `41fb6f8f0d74213023e9182b2a62a15a8c5782a34707310f09be67295bca27b9`，含全部旧收据当前SHA与HEAD逐一相等校验。

复跑：
```sh
python3 -B multi_asset/exports/research/acting_lead_2026-09-27/devices/test_d10_first_span_identity.py
```

funding新独立消费者应钉本次新sourceSHA，继续使用原identity manifest；不得把输入门的PASS写成现金执行PASS。仍未部署首120检查器或新cash消费者。
