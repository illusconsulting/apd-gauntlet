---
framework_version: 1.0.0
run_id: test-attack-path-minimal
domain_pack: { name: pbm, version: 1.0.0 }
artifacts:
  - { filename: tech_plan.md, type: tech_plan }
  - { filename: "40-synthesis/asset-graph.yaml",   type: derived }
  - { filename: "40-synthesis/attack-paths.yaml",  type: derived }
  - { filename: "40-synthesis/defense-graph.yaml", type: derived }
---

# Minimal-run context brief (test fixture)

Lists every artifact the specialist + analyzer findings cite as evidence so
``validate.run_cross_file_pass`` (``evidence[i].artifact not in intake brief``)
does not flag them. Used by the attack-path C-10/C-15 test suite.
