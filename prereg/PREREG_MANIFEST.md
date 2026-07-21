# Additional File 5: pre-registration SHA-256 manifest

Every pre-registration in `prereg/` is frozen by a companion `SHA256_LOCK_*.json` that records the SHA-256 of the locked file's committed bytes. This manifest is generated and checked by `scripts/prereg_manifest.py`, which recomputes each hash from source and asserts it against the lock; the check runs in continuous integration on every commit and in `make repro`.

Verify any row from a clean checkout:

```
sha256sum <file>            # must equal the SHA-256 column
python scripts/prereg_manifest.py --check   # re-hash every entry, assert this manifest
```

Total: 120 locked files across 80 pre-registration locks; 116 re-hash against the current committed bytes and are asserted here. 4 belong to the superseded phase-0 origin seal (listed at the end).

## Table 3 honesty-ledger pre-registrations

The ten claims in Table 3, each with the committed pre-registration that fixed it before scoring and that pre-registration's SHA-256.

| # | Claim | Verdict | Pre-registration | SHA-256 |
|---|---|---|---|---|
| 1 | Human K562 head, exact-site resolution | PASS | `prereg/ws_expr2.yaml` | `c9966059cee6d241beaacb2745d298ae5e1fc6d42abf0a22311e5e7266f6b90f` |
| 2 | Mouse-trained axis transfers to human | NULL | `prereg/ws_expr2.yaml` | `c9966059cee6d241beaacb2745d298ae5e1fc6d42abf0a22311e5e7266f6b90f` |
| 3 | Validated head realisable at served resolution | FAIL | `prereg/ws_expr2.yaml` | `c9966059cee6d241beaacb2745d298ae5e1fc6d42abf0a22311e5e7266f6b90f` |
| 4 | Positional-silencing classifier | NULL | `prereg/ws_expr2.yaml` | `c9966059cee6d241beaacb2745d298ae5e1fc6d42abf0a22311e5e7266f6b90f` |
| 5 | Locus score ranks harbours above bulk genome | NULL | `prereg/ws_priorart.yaml` | `c7469b50e80b6950ee96441d384ae1d2228ecf5f78e043fd1622baf42ee45233` |
| 6 | Locus score vs confounder-matched controls | PASS (weak) | `prereg/ws_a.yaml` | `b88d4bf4f8a4bcc438728bca72310f8f21bdff956746c13376610b3f1cd98d3d` |
| 7 | Locus score predicts clinical genotoxicity | FALSE NEGATIVES | `prereg/ws_priorart.yaml` | `c7469b50e80b6950ee96441d384ae1d2228ecf5f78e043fd1622baf42ee45233` |
| 8 | Writer model beats baseline across families | GATE FAILED | `prereg/ws_writer.yaml` | `8997a447b35aa1b78e43dcd40cd6893b4c083a9b54bb4d70286c91cd185db4f4` |
| 9 | Serine-integrase learned model (both metrics) | NULL (strict) | `prereg/ws_offtarget2.yaml` | `a351a409b191df1755a2a48e00a23116a9d72d3d0ee9c576bedf5710092cf2c5` |
| 10 | Expected-information-gain beats random | SPANS ZERO | `prereg/ws_closedloop.yaml` | `ad9d413e5f790d64affb41a6bda2e2843fcbb5a2289e780b19c8bbe89dc69f3c` |

## Full manifest: every current pre-registration lock

Each file below re-hashes to the SHA-256 shown; `scripts/prereg_manifest.py` asserts this on every commit.

| Registration | Lock | File | SHA-256 |
|---|---|---|---|
| phase 1.5 | `SHA256_LOCK_phase1_5.json` | `configs/bridge_offtarget_profile.yaml` | `bb3a19515c80ca099aa1028d84200bacc9649f6d430d26b5afb119361b50a71f` |
| phase 1.5 | `SHA256_LOCK_phase1_5.json` | `data/curated/bridge_offtarget_profile_measured.parquet` | `b065e68b7437cbc6b2e14a6860d5454862a67f3e8221ef2daf500fc5f09e4076` |
| phase 1.5 | `SHA256_LOCK_phase1_5.json` | `prereg/paper4.yaml` | `a643c392f5618906f39900fa01764297dea46d0773877f79f6fc3ed9393e4fe1` |
| phase 2 | `SHA256_LOCK_phase2.json` | `configs/atlas_families.yaml` | `de374812909c8b153d4c6199bd1c9afb27f48d5f596947a69ea0790c07f64d08` |
| phase 2 | `SHA256_LOCK_phase2.json` | `configs/monitor_queries.yaml` | `38c934b3c61e7e7b7b6a4336d735d2f527d737b7760fe2ae106492495b07e86c` |
| phase 2 | `SHA256_LOCK_phase2.json` | `configs/score_axes.yaml` | `c913a2c33d9882c25fc460158b643b4ed1a439d0dc72cd800779353ab9ed1957` |
| phase 2 | `SHA256_LOCK_phase2.json` | `pen_stack/mech/pfam_whitelist.yaml` | `52e789566054a517368b3d31fc8b578c5482a0de29d611a0625f0699c9af0845` |
| phase 2 | `SHA256_LOCK_phase2.json` | `prereg/paper2.yaml` | `9ca9dc5e9446cf84db82fb611f1b5d8b9b0c6d49adf9dc7143f27d4001096fe8` |
| phase 3 | `SHA256_LOCK_phase3.json` | `configs/delivery_rules.yaml` | `a6acbde9148e104faa29c1b6b197d31f5fa332b2038697c72dc112d752096119` |
| phase 3 | `SHA256_LOCK_phase3.json` | `configs/intent_weights.yaml` | `9c2e6ee3b9eaea9c9e54097e773f44c400e800464f5b0798e54b45ec6dd52385` |
| phase 3 | `SHA256_LOCK_phase3.json` | `data/benchmark_panel.csv` | `60d33f60081b7d0d08f0f66e0610746412d39e0c1f00f1febf71dccc33a4f801` |
| phase 3 | `SHA256_LOCK_phase3.json` | `prereg/paper3.yaml` | `454de44c9f3ba4385428d65756b13a8118c7570085d893bbef8c9d16e6a436e7` |
| WS-A | `SHA256_LOCK_ws_a.json` | `configs/gsh_validated_heldout.yaml` | `0fa2a46952826f2a4ff55cccea9318be3581edde020832b0905e4e56c1226641` |
| WS-A | `SHA256_LOCK_ws_a.json` | `data/gsh_matched_controls.parquet` | `865b18ff23d140c3df6f3b5f25398581ebdfe3534e1cecf6f512afb540ab5ede` |
| WS-A | `SHA256_LOCK_ws_a.json` | `data/writer_panel.csv` | `cc69a06b02d1a4902c8cf994487ab7ed17d674e28389fb10f25bb6614bc752dc` |
| WS-A | `SHA256_LOCK_ws_a.json` | `prereg/ws_a.yaml` | `b88d4bf4f8a4bcc438728bca72310f8f21bdff956746c13376610b3f1cd98d3d` |
| WS-ACQ | `SHA256_LOCK_ws_acq.json` | `prereg/ws_acq.yaml` | `2619b7a4d343f9c31b269a7c6ad5ac4f7b6aa0451776790b02f9353659420cee` |
| WS-DESIGN | `SHA256_LOCK_ws_aldesign.json` | `prereg/ws_aldesign.yaml` | `95a6b805a950c3d4e2a00113ae61002e3c38488261f208aceef1b7443dbef568` |
| WS-VALIDATE | `SHA256_LOCK_ws_alvalidate.json` | `prereg/ws_alvalidate.yaml` | `ef8bd5b68c3e7522b2b891e7de4bf742234e1d97d57e3d225b423f8321f9af8c` |
| WS-ATLAS | `SHA256_LOCK_ws_atlas.json` | `prereg/ws_atlas.yaml` | `b8024f01cab7581fc8c3aa4917c9402f6418f4fa27f4ebb067cf9e4a2067ce57` |
| WS-B | `SHA256_LOCK_ws_b.json` | `configs/gsh_validated_heldout.yaml` | `0fa2a46952826f2a4ff55cccea9318be3581edde020832b0905e4e56c1226641` |
| WS-B | `SHA256_LOCK_ws_b.json` | `data/gsh_matched_controls.parquet` | `865b18ff23d140c3df6f3b5f25398581ebdfe3534e1cecf6f512afb540ab5ede` |
| WS-B | `SHA256_LOCK_ws_b.json` | `prereg/ws_a.yaml` | `b88d4bf4f8a4bcc438728bca72310f8f21bdff956746c13376610b3f1cd98d3d` |
| WS-B | `SHA256_LOCK_ws_b.json` | `prereg/ws_b.yaml` | `d7a4f275360e4e53e3ebdc805270f76438d20e09202ef3cc556c9bd5840810cc` |
| WS-BA | `SHA256_LOCK_ws_ba.json` | `benchmarks/genome_writing_bench/tasks.yaml` | `5caf0993da12c0c02614f392491af6826356880bc06e9d4cd37d3359306a1706` |
| WS-BA | `SHA256_LOCK_ws_ba.json` | `prereg/ws_ba.yaml` | `a43e7f1585c03dcbc5ba40df3e3a37cdff1a86bb3378eaf65d86bbbfa646fd66` |
| WS-BA | `SHA256_LOCK_ws_ba_v33.json` | `benchmarks/genome_writing_bench/tasks.yaml` | `5caf0993da12c0c02614f392491af6826356880bc06e9d4cd37d3359306a1706` |
| WS-BA | `SHA256_LOCK_ws_ba_v33.json` | `prereg/ws_ba_v33.yaml` | `234ed9de5d1e91529ad039fbc1e95afe030f735dd763bdb3aab20d5f3cade576` |
| WS-BA-graph | `SHA256_LOCK_ws_ba_v45.json` | `prereg/ws_ba_v45.yaml` | `1b731ab3256f5c523a08a705caff345f98b86d0790af4f0eee59a9fdf3cdf7e8` |
| WS-BENCH | `SHA256_LOCK_ws_bench.json` | `prereg/ws_bench.yaml` | `24012e8a49db872944842ec53e2018bfaee973f3608d8be88fb82aa05ee3bc48` |
| WS-C | `SHA256_LOCK_ws_c.json` | `docs/alphagenome_feasibility.md` | `3baca6a482ee958b23e5b791534291324a0beb084ebf7de35149db1ef9667bf0` |
| WS-C | `SHA256_LOCK_ws_c.json` | `prereg/ws_c.yaml` | `d07a011aa576dd8ae35de18455e4d61eb30b1dfd96055f6a1c235d2394e16587` |
| WS-CAL | `SHA256_LOCK_ws_cal.json` | `prereg/ws_cal.yaml` | `aaacb7785a111165254154f1734029464fe1a0b5ef25093b3620a057d962ae05` |
| WS-CALIB | `SHA256_LOCK_ws_calib.json` | `prereg/ws_calib.yaml` | `290362570d766812b6e9e8250b9f2ba84e7a01c812d2c92ff7e49af1a964c503` |
| WS-CHALLENGE | `SHA256_LOCK_ws_challenge.json` | `prereg/ws_challenge.yaml` | `2eaceb5990d769e7886a1aeb4d6f2399b2ea2c750fe603eab101736c6590ed67` |
| WS-CHAT | `SHA256_LOCK_ws_chat.json` | `prereg/ws_chat.yaml` | `8a9a27e6ddf6f0d53ceb5f9a8cc67dfb4e6ef7bda4b8434e1013712a21d71202` |
| WS-CITE-GEN | `SHA256_LOCK_ws_cite.json` | `prereg/ws_cite.yaml` | `e46e34df8ca288a644f7bbf023d94de813d8cf235cfdb92b72515129f37a68a5` |
| WS-CLOSEDLOOP | `SHA256_LOCK_ws_closedloop.json` | `prereg/ws_closedloop.yaml` | `ad9d413e5f790d64affb41a6bda2e2843fcbb5a2289e780b19c8bbe89dc69f3c` |
| WS-CONTINUAL | `SHA256_LOCK_ws_continual.json` | `prereg/ws_continual.yaml` | `232e5f69ebf339d8df6123ab176661d587c2f13378864ac94912733036d42c58` |
| WS-COSCI2 | `SHA256_LOCK_ws_cosci2.json` | `prereg/ws_cosci2.yaml` | `9e9b5bbe82e8ef555c6f50af153669f39de5679878de6d8149f43fc1fd9d6439` |
| WS-CRIT-SCOPE2 | `SHA256_LOCK_ws_crit.json` | `prereg/ws_crit.yaml` | `9820e58fb7d8458d381e863dfb1b6b2c4fdf0491c5de6fa7e9e422f13d181649` |
| WS-CT | `SHA256_LOCK_ws_ct.json` | `prereg/ws_ct.yaml` | `61d32f7bbf5ba0dda3d77249718d60bff1b9e5fe3b314dfbd9d2e9cf3762e964` |
| WS-D | `SHA256_LOCK_ws_d.json` | `configs/delivery_vehicles.yaml` | `755f1b3c1cf6e0d14c10de2a708ddd79aacaa2373ab563657293f08453d8d3c1` |
| WS-D | `SHA256_LOCK_ws_d.json` | `configs/rules/delivery.yaml` | `b8ff8f5d2b189265b1e330acf12b813398b5247b1328fee82d4998accbca9964` |
| WS-D | `SHA256_LOCK_ws_d.json` | `prereg/ws_d.yaml` | `44a5148699700fcf55bfe08e619a9c4d5bf5761421d6692edd1f12f337c91bdc` |
| WS-DELIVERY | `SHA256_LOCK_ws_delivery.json` | `prereg/ws_delivery.yaml` | `c5dea2f7907f89aac5296568c41777b8f7fc4aca2b38c3f5ded82ebef357f261` |
| WS-DRIFT | `SHA256_LOCK_ws_drift.json` | `prereg/ws_drift.yaml` | `747801c9e2ba31af088308f9aa4e784d4c62f1b17325f7135a8c6d7e0caa8c0b` |
| WS-E | `SHA256_LOCK_ws_e.json` | `benchmarks/genome_writing_bench/tasks.yaml` | `5caf0993da12c0c02614f392491af6826356880bc06e9d4cd37d3359306a1706` |
| WS-E | `SHA256_LOCK_ws_e.json` | `prereg/ws_e.yaml` | `d6c550a97bd3b2f621f40904343d88b38e459096a0db15a35b123e6a68e57315` |
| WS-ENV | `SHA256_LOCK_ws_env.json` | `prereg/ws_env.yaml` | `b5a051fe6f7bf7c8da785023f0670ac405c4c5792dc4d2de07ddd7cbeae155be` |
| WS-EP | `SHA256_LOCK_ws_ep.json` | `configs/known_unknowns.yaml` | `46c47159aefe19cd3ca8e5ae822a0959f962050bfa921fb71a8d17660669be55` |
| WS-EP | `SHA256_LOCK_ws_ep.json` | `prereg/ws_ep.yaml` | `1ee89f9d43aff331c320b431b515d675a8b6efa9ed533c998fd02ae83c853447` |
| WS-EPITOPE | `SHA256_LOCK_ws_epitope.json` | `prereg/ws_epitope.yaml` | `d69f145f8cfe80ae2c0bccbde17dc85ccdff31f354b0db0a6a9a10910d6b31e3` |
| WS-EXPRESS2 | `SHA256_LOCK_ws_expr2.json` | `prereg/ws_expr2.yaml` | `c9966059cee6d241beaacb2745d298ae5e1fc6d42abf0a22311e5e7266f6b90f` |
| WS-F | `SHA256_LOCK_ws_f.json` | `prereg/ws_f.yaml` | `b115a7887433fe1c2ad5c3d1adf4d09736847daeeb1b2cbbb995d851443fba5b` |
| WS-FRONTEND | `SHA256_LOCK_ws_frontend.json` | `prereg/ws_frontend.yaml` | `983be0d5b0e7016685fa675db82ea6586df3c20673e5723ecb09f84a0a56fe6a` |
| WS-G | `SHA256_LOCK_ws_g.json` | `prereg/ws_g.yaml` | `595b2d9ae1ba6dd4bf808ed3ab496245e7bd5d73ee303a0427813f89abee92b4` |
| WS-GEN | `SHA256_LOCK_ws_gen.json` | `prereg/ws_gen.yaml` | `2419889761968268d1a958f4826c49c7d1a87c98a8da3359799776d174ff3df0` |
| WS-GENOTOX | `SHA256_LOCK_ws_genotox.json` | `prereg/ws_genotox.yaml` | `4cd8534034fd42986708345eb911bdf62200d0a9c528f80378b29920b4ce434b` |
| WS-G-knowledge-graph | `SHA256_LOCK_ws_graph.json` | `prereg/ws_graph.yaml` | `381a5aa29b13bfb12463500eecdfc687043839f7264ed353716038287507d7ea` |
| WS-H | `SHA256_LOCK_ws_h.json` | `prereg/ws_h.yaml` | `a24f6087f266b33724c7468cc2cf92794f02fae7f0f25b4656f3fb9890b31f23` |
| WS-HYBRID | `SHA256_LOCK_ws_hybrid.json` | `prereg/ws_hybrid.yaml` | `98b8b816bfbb322e70f6cd6edb173218a6aa3a7c7fbaba1ebbf8d5d05dba47de` |
| WS-IMMUNE | `SHA256_LOCK_ws_immune.json` | `prereg/ws_immune.yaml` | `9e6f487a8d59257af2b580dea21e4406d2879a5c5fa5a8145b276f995041d6b2` |
| WS-IMMUNE2 | `SHA256_LOCK_ws_immune2.json` | `prereg/ws_immune2.yaml` | `503d5dc30ef41c77f80058c5914b4faddd5245d2bf3c3aee3c2e1a61231a1a11` |
| WS-INGEST | `SHA256_LOCK_ws_ingest.json` | `prereg/ws_ingest.yaml` | `3e95dc975010d8b83f25babb8fdc5a6839a88725b063f2d6c7163925e35d10a3` |
| WS-INNATE | `SHA256_LOCK_ws_innate.json` | `prereg/ws_innate.yaml` | `732ed00254b8caf2f0edca0eb3e1dc697e480c1a9f59556d5fea654e39ee5b09` |
| WS-LOOP | `SHA256_LOCK_ws_loop.json` | `prereg/ws_loop.yaml` | `a8bb5f8249cceea55f949fc8e6a1e34581c478b93fb0c048b27fc1500ae05552` |
| WS-MANIFEST | `SHA256_LOCK_ws_manifest.json` | `prereg/ws_manifest.yaml` | `8054eba7d580a91b2464fa5502dc876fd1f8ef6c27e46e116072633ed36e72b6` |
| WS-MC | `SHA256_LOCK_ws_mc.json` | `configs/delivery_constraints.yaml` | `92c07644cf044106d9abf6b116dee3e981be0e35605efafb566a0af988e4fad6` |
| WS-MC | `SHA256_LOCK_ws_mc.json` | `configs/target_sites.yaml` | `cfc0bc484866cbaaeaf2b6f10f586af2e75dc4ceab1d5b18fee4d1f42aff8dd6` |
| WS-MC | `SHA256_LOCK_ws_mc.json` | `prereg/ws_mc.yaml` | `bc38a5bbdb460b0f73aba307942c985b05b98d74c8785d0deffb894aa15b004d` |
| WS-MCP | `SHA256_LOCK_ws_mcp.json` | `prereg/ws_mcp.yaml` | `930c570764ab2e5f0d43716163d4a13f4d6c0ddaf68a655693e3b6629d7de0cc` |
| WS-MECH | `SHA256_LOCK_ws_mech.json` | `prereg/ws_mech.yaml` | `28201949c0713ed5a10eda00d8a38ccf6e43d2c1bffb9b5951ae94f7eba3491a` |
| WS-MON | `SHA256_LOCK_ws_mon.json` | `prereg/ws_mon.yaml` | `08b7b1cb87fc1559e3235ff3b6ca79727c89281df2bce8b2b89b45bbe6f772e5` |
| WS-O | `SHA256_LOCK_ws_o.json` | `prereg/ws_o.yaml` | `5e06aff963c64965963c8b79f7ad209a6a64023ad3a1b7d5faee1f3a3d02303e` |
| WS-OFFTARGET | `SHA256_LOCK_ws_offtarget.json` | `prereg/ws_offtarget.yaml` | `60122b82869d13c0265db61d56b6fe3a4c5e62e39cf796b2315ecfa9a39b558b` |
| PEN-OFFTGT-v2 | `SHA256_LOCK_ws_offtarget2.json` | `prereg/ws_offtarget2.yaml` | `a351a409b191df1755a2a48e00a23116a9d72d3d0ee9c576bedf5710092cf2c5` |
| WS-OPENAPI | `SHA256_LOCK_ws_openapi.json` | `prereg/ws_openapi.yaml` | `142f148bec9b143420918159dd81fed7fe4868ac1118ef05a1603da6f941e5f8` |
| WS-ORACLE | `SHA256_LOCK_ws_oracle.json` | `prereg/ws_oracle.yaml` | `5dec46ba0649bc4a8470ca06ca7cd2df7ce3c4c6998d16a4aef8256d4feeabfb` |
| WS-ORCH | `SHA256_LOCK_ws_orch.json` | `prereg/ws_orch.yaml` | `e5e5aeb88674188a1899ce07c05cc80f8652a1c4bc5f9e823cf6bdeaefce1cd3` |
| WS-OUTCOME | `SHA256_LOCK_ws_outcome.json` | `prereg/ws_outcome.yaml` | `63698da872947259738a898cd05f908c62c50a21e67bb371b7cc598fc397a1a3` |
| WS-PARETO | `SHA256_LOCK_ws_pareto.json` | `prereg/ws_pareto.yaml` | `dbff0572f0217d86eb2e267d76589a037222c3ac89e5438f078824c765899e25` |
| WS-PEG | `SHA256_LOCK_ws_peg.json` | `prereg/ws_peg.yaml` | `ab36af05cb0ca29ab5bd7e8dea5bff64403bab6198e25054f797b57b0c2562af` |
| PEN-CHAT | `SHA256_LOCK_ws_penchat.json` | `data/rag_corpus.parquet` | `44594399d7095494aaee63282f61235df266f58913f409a8bb8d363abf0ed8b1` |
| PEN-CHAT | `SHA256_LOCK_ws_penchat.json` | `prereg/ws_penchat.yaml` | `5ce11c0fcc11c18a426ff5006a6ae281d1161810c0aed24f25929e43d6357bc0` |
| WS-PLAN-MULTI | `SHA256_LOCK_ws_plan.json` | `prereg/ws_plan.yaml` | `20f4edec2bfc719356df705e578a427a4e82865d6986ffbd97892929bbb969d8` |
| WS-POLICY | `SHA256_LOCK_ws_policy.json` | `configs/safety/policy.yaml` | `4f4d560b71154c8e7680073db4ed9bd5ab6e91e3a01fcec287c45759be9a0545` |
| WS-POLICY | `SHA256_LOCK_ws_policy.json` | `prereg/ws_policy.yaml` | `46e7606572a4da6b2a4d0b160def9c93393c69df332ce12eac0b8ed752c3a036` |
| WS-PRIORART | `SHA256_LOCK_ws_priorart.json` | `prereg/ws_priorart.yaml` | `c7469b50e80b6950ee96441d384ae1d2228ecf5f78e043fd1622baf42ee45233` |
| WS-PROFILE | `SHA256_LOCK_ws_profile.json` | `prereg/ws_profile.yaml` | `357c3683bf25f6d48d44d7fe1130be29b224d1c67b0dcf509def8b50b41f1bff` |
| WS-PROTO | `SHA256_LOCK_ws_proto.json` | `prereg/ws_proto.yaml` | `2e98a82345cf744c0b79a0c0b84dae746c1269755f0c4a84624a9ca2087dbb7c` |
| WS-R | `SHA256_LOCK_ws_r.json` | `configs/delivery_vehicles.yaml` | `755f1b3c1cf6e0d14c10de2a708ddd79aacaa2373ab563657293f08453d8d3c1` |
| WS-R | `SHA256_LOCK_ws_r.json` | `configs/rules/delivery.yaml` | `b8ff8f5d2b189265b1e330acf12b813398b5247b1328fee82d4998accbca9964` |
| WS-R | `SHA256_LOCK_ws_r.json` | `configs/rules/fold.yaml` | `84c0f2b35299fca98319a42a8d6f9a74ed91a9db55e540bff3af766f4a85d6d5` |
| WS-R | `SHA256_LOCK_ws_r.json` | `configs/rules/multiplex.yaml` | `22e8fcfa0e197169e46e7a545a8ab0d5730d08129e5250490bc17716aca54721` |
| WS-R | `SHA256_LOCK_ws_r.json` | `configs/rules/payload.yaml` | `9c882c3ebf851d78f4ee7d975a858ec8f47d43d9de19308a1271454c0eac6b67` |
| WS-R | `SHA256_LOCK_ws_r.json` | `configs/rules/reachability.yaml` | `d316557dfcce86872612dc6aaa3672b3004243c804bded52dbed2d3d715c43fb` |
| WS-R | `SHA256_LOCK_ws_r.json` | `prereg/ws_r.yaml` | `01a88e80856f6eaef01517871da1c29942aafe258fe09b5703c9a2f18f68b409` |
| WS-REDTEAM | `SHA256_LOCK_ws_redteam.json` | `configs/safety/probes.yaml` | `88f3728044913a0559f7900582071e11b7a8e483c313f75b82a2133852887b3b` |
| WS-REDTEAM | `SHA256_LOCK_ws_redteam.json` | `prereg/ws_redteam.yaml` | `1272713c6070eda46fd5d5316a96a7c564bff9fdb9bc5e7788007feb792b4ca4` |
| WS-ROUTE | `SHA256_LOCK_ws_route.json` | `configs/write_types.yaml` | `f0870bd31b782aadd2b5dcf8b5e9319ff74042dfb15bf4068adbed2816aafcad` |
| WS-ROUTE | `SHA256_LOCK_ws_route.json` | `prereg/ws_route.yaml` | `5be122e7962921cf82dda19152f538ca55fc0215e4039f67ce0865de106dc4e9` |
| WS-SCREEN | `SHA256_LOCK_ws_screen.json` | `configs/safety/hazard_registry.yaml` | `a1d22d4cd13d9998132af3cbc9c62de80f42d99a6b86562586c66a5638b24e28` |
| WS-SCREEN | `SHA256_LOCK_ws_screen.json` | `configs/safety/probes.yaml` | `88f3728044913a0559f7900582071e11b7a8e483c313f75b82a2133852887b3b` |
| WS-SCREEN | `SHA256_LOCK_ws_screen.json` | `prereg/ws_screen.yaml` | `475b63fd2e961e093f7686dc9fc04718a626a26a6e699b83961a8312d2311dd4` |
| WS-SEROPREV | `SHA256_LOCK_ws_seroprev.json` | `prereg/ws_seroprev.yaml` | `18cc27da5b6aee682195e9c57abff49ca1d6338b71d5ac7c4b87084d25fa803b` |
| WS-SIMLAB | `SHA256_LOCK_ws_simlab.json` | `prereg/ws_simlab.yaml` | `d9caad2df477605dca1dee1f4a30b0da297c0033cb7c89230fea8e5cf603edf7` |
| WS-CAL (twin) | `SHA256_LOCK_ws_twincal.json` | `prereg/ws_twincal.yaml` | `d16ff13d473135d964e17897c3da72a1b508668148b2fac73d4bbf54e8dcd667` |
| WS-UQ | `SHA256_LOCK_ws_uq.json` | `prereg/ws_b.yaml` | `d7a4f275360e4e53e3ebdc805270f76438d20e09202ef3cc556c9bd5840810cc` |
| WS-UQ | `SHA256_LOCK_ws_uq.json` | `prereg/ws_uq.yaml` | `b25473910dde1081ef0c8317cbbc3dad01b3d79c0888d639b874f518419fbe03` |
| WS-V | `SHA256_LOCK_ws_v.json` | `prereg/ws_v.yaml` | `d90cbb28f8da4e39ed6fb93f9d7cd41bf7e6a374cb47bf78d45f7884a8864642` |
| WS-VCELL | `SHA256_LOCK_ws_vcell.json` | `prereg/ws_vcell.yaml` | `a2e02b1ab9a46c802ff3867bd0fccf8849ce1f87667c6af49ad43b7f8202ae63` |
| WS-VERIFY | `SHA256_LOCK_ws_verify.json` | `prereg/ws_verify.yaml` | `6ea46ecf1c5ef7fbd9072fc7ebfc17b419c8ce9f1bbb846ea37bbbfbbd395294` |
| WS-WRITER | `SHA256_LOCK_ws_writer.json` | `prereg/ws_writer.yaml` | `8997a447b35aa1b78e43dcd40cd6893b4c083a9b54bb4d70286c91cd185db4f4` |
| WS-WRITESPEC | `SHA256_LOCK_ws_writespec.json` | `prereg/ws_writespec.yaml` | `53d754f68d5662d6dbee88d858bd370f1f55fd8af0b220577d3dd6096079cf4d` |
| WS-WV | `SHA256_LOCK_ws_wv.json` | `prereg/ws_wv.yaml` | `506f59a1e2b215ccb120c299cb425bead6f97fc1eb8bf5063060a8a7d5a96fa6` |

## Superseded phase-0 origin seal

The phase-0 lock is the programme origin seal. All 4 of its inputs were revised in later cycles, so the phase-0 hashes below are the sealed originals and no longer match the current files. 1 stayed in use and is re-locked at the current bytes by a later-cycle lock (asserted in the manifest above): `configs/score_axes.yaml`. The other 3 are not re-locked at their current bytes by any later lock, so only the phase-0 originals are recorded here: `configs/universe_crosswalk.yaml`, `configs/wtkb_curated.yaml`, `prereg/phase0.yaml`.

| Lock | File | Sealed SHA-256 (phase 0) | Current status |
|---|---|---|---|
| `SHA256_LOCK_phase0.json` | `configs/score_axes.yaml` | `77147ea1f015512767557332d55a10aa389ffc49bc87dd402912657d666b1ad3` | re-locked at current bytes above |
| `SHA256_LOCK_phase0.json` | `configs/universe_crosswalk.yaml` | `fb6667173a3a5c150e4fb5f75f0ba0f49e60d8ea89190ff2a9de2d04ac3c2568` | not re-locked by a later lock |
| `SHA256_LOCK_phase0.json` | `configs/wtkb_curated.yaml` | `bba67cff3c6d128e0146b103f82bf9479a00cd4d54450b46799453dba6669a5d` | not re-locked by a later lock |
| `SHA256_LOCK_phase0.json` | `prereg/phase0.yaml` | `c21dbbcfc6f586fd4aa1d32f5e4816e2ae7eaaecda5425323174c9ef90ab028b` | not re-locked by a later lock |

