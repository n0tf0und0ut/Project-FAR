health:
	python tools/repo_health_check.py --full
	python tools/check_investigation_execution.py
	python tools/generate_investigation_index.py --check
	python tools/check_research_gates.py
	python tools/check_deduction_first_program.py
	python tools/check_thm_target_001.py
	python tools/check_faithful_representation.py
	python tools/check_p8_theorem_role.py
	python tools/check_s_core_lemma_ledger.py
	python tools/check_s_core_w0.py
	python tools/check_fara_primitive_independence.py
	python tools/check_project_far_theory_closure.py
	python tools/check_fara_w4_representation.py
	python tools/check_fara_w5_invariance.py
	python tools/check_fara_core_formalization.py
	python tools/check_s_core_w1.py
	python tools/check_s_core_w2.py
	python tools/check_s_core_w3.py
	python tools/check_s_core_w4.py
	python tools/check_s_core_w5.py
	python tools/check_s_core_w5_mechanization.py
	python tools/check_post_w5_universal_structure_program.py
	python tools/check_w3_5_corpus_freeze.py
	python tools/check_w3_5_factorization.py
	python tools/check_w3_5_specificity.py
	python tools/check_w3_5_candidate_tests.py
	python tools/check_representation_discovery_separation.py
	python tools/check_candidate_architectures.py
	python tools/check_reasoning_domain.py
	python tools/check_independent_reasoning_definition.py
	python tools/check_preservation_basis.py
	python tools/check_pb001_test_suite.py
	python tools/check_pb001_execution.py
	python tools/check_pbts001_replication_package.py
	python tools/check_pbts001_replication_run001_controls.py
	python research/theory-dependency-audit/execute.py
	python -m unittest tests.test_theory_dependency_audit -v

health-fast:
	python tools/repo_health_check.py --fast
	python tools/check_investigation_execution.py
	python tools/generate_investigation_index.py --check
	python tools/check_research_gates.py
	python tools/check_deduction_first_program.py
	python tools/check_thm_target_001.py
	python tools/check_faithful_representation.py
	python tools/check_p8_theorem_role.py
	python tools/check_s_core_lemma_ledger.py
	python tools/check_s_core_w0.py
	python tools/check_fara_primitive_independence.py
	python tools/check_project_far_theory_closure.py
	python tools/check_fara_w4_representation.py
	python tools/check_fara_w5_invariance.py
	python tools/check_s_core_w1.py
	python tools/check_s_core_w2.py
	python tools/check_s_core_w3.py
	python tools/check_s_core_w4.py
	python tools/check_s_core_w5.py
	python tools/check_s_core_w5_mechanization.py
	python tools/check_post_w5_universal_structure_program.py
	python tools/check_w3_5_corpus_freeze.py
	python tools/check_w3_5_factorization.py
	python tools/check_w3_5_specificity.py
	python tools/check_w3_5_candidate_tests.py
	python tools/check_representation_discovery_separation.py
	python tools/check_candidate_architectures.py
	python tools/check_reasoning_domain.py
	python tools/check_independent_reasoning_definition.py
	python tools/check_preservation_basis.py
	python tools/check_pb001_test_suite.py
	python tools/check_pb001_execution.py
	python tools/check_pbts001_replication_package.py
	python tools/check_pbts001_replication_run001_controls.py
	python research/theory-dependency-audit/execute.py
	python -m unittest tests.test_theory_dependency_audit -v

docs-check:
	python tools/validate_docs.py

final-newline-check:
	python tools/check_final_newline.py

links-check:
	python tools/check_internal_links.py
	python tools/check_post_swe_agent_v2_stabilization.py

math-check:
	python tools/check_math_rendering.py

release-check:
	python tools/check_release_consistency.py

research-check:
	python tools/reconcile_research_corpus.py
	python tools/far_research_registry.py
	python tools/check_far_core_v11_formalization.py
	python tools/research_campaign.py
	python tools/check_fara_foundation_comparison.py
	python tools/check_research_gates.py
	python tools/check_investigation_execution.py
	python tools/generate_investigation_index.py --check
	python tools/check_deduction_first_program.py
	python tools/check_thm_target_001.py
	python tools/check_faithful_representation.py
	python tools/check_p8_theorem_role.py
	python tools/check_s_core_lemma_ledger.py
	python tools/check_s_core_w0.py
	python tools/check_fara_primitive_independence.py
	python tools/check_project_far_theory_closure.py
	python tools/check_fara_w4_representation.py
	python tools/check_fara_w5_invariance.py
	python tools/check_s_core_w1.py
	python tools/check_s_core_w2.py
	python tools/check_s_core_w3.py
	python tools/check_s_core_w4.py
	python tools/check_s_core_w5.py
	python tools/check_s_core_w5_mechanization.py
	python tools/check_post_w5_universal_structure_program.py
	python tools/check_w3_5_corpus_freeze.py
	python tools/check_w3_5_factorization.py
	python tools/check_w3_5_specificity.py
	python tools/check_w3_5_candidate_tests.py
	python tools/check_representation_discovery_separation.py
	python tools/check_candidate_architectures.py
	python tools/check_reasoning_domain.py
	python tools/check_independent_reasoning_definition.py
	python tools/check_preservation_basis.py
	python tools/check_pb001_test_suite.py
	python tools/check_pb001_execution.py
	python tools/check_pbts001_replication_package.py
	python tools/check_pbts001_replication_run001_controls.py
	python research/theory-dependency-audit/execute.py
	python -m unittest tests.test_theory_dependency_audit -v

.PHONY: far-research-infrastructure-check
far-research-infrastructure-check:
	python tools/far_research_registry.py
	python tools/check_far_core_v11_formalization.py
	python tools/research_campaign.py
	python -m unittest tests.test_far_research_infrastructure tests.test_far_core_v11_formalization -v

status:
	python tools/project_status_report.py

gaps:
	python tools/detect_research_gaps.py

plan:
	python tools/self_advancement_plan.py


dashboard:
	python tools/self_advancement_plan.py

release-readiness:
	python tools/release_readiness_report.py

test:
	python tools/run_tests.py

test-fast:
	python tools/run_tests.py --fast

# Local runs bypass the result cache, as CI does: cache keys cover only declared check inputs, not
# the modules a check imports, so a cached PASS can be stale (see docs/audits/root-of-trust-audit-2026-09.md).
validate:
	python -m far_validation validate --profile pr-fast --no-cache

validate-changed:
	python -m far_validation validate --profile pr-fast --changed origin/main --explain --no-cache

validate-full:
	python -m far_validation validate --profile pr-full --no-cache

validate-release:
	python -m far_validation validate --profile release --no-cache

validate-doctor:
	python -m far_validation doctor

validate-diagnose:
	python -m far_validation diagnose

validate-trace:
	python -m far_validation validate --profile pr-full --no-cache --trace-dependencies --require-trace

validate-oracle:
	python -m far_validation oracle

validate-weakening:
	python -m far_validation weakening --base origin/main

validate-mutations:
	python -m far_validation mutations --report artifacts/validation/runtime/mutation-campaign.json

validate-formal:
	python -m far_validation formal --max-checks 4
	lean mechanization/lean/ValidationEngine.lean

validate-assurance:
	python validation_bootstrap/verify.py
	python -m unittest discover -s tests -p "test_validation_assurance.py" -v
	python -m far_validation oracle
	python -m far_validation weakening --base origin/main
	python -m far_validation formal --max-checks 4
	python -m far_validation mutations --report artifacts/validation/runtime/mutation-campaign.json

validate-certificate:
	python -m far_validation certificate verify --require-signed --expected-commit "$$(git rev-parse HEAD)" --expected-tree "$$(git rev-parse HEAD^{tree})"

cre001-deterministic:
	python tools/cre001_compile_vocabularies.py --write --check

cre002-execute:
	python tools/cre002_execute.py --write --check

semantic-check:
	python tools/check_project_far_theory_closure.py
	python tools/check_fara_foundation_comparison.py
	python tools/check_semantic_consistency.py
	python tools/check_fara_operator_w2.py
	python tools/check_fara_common_architecture_w3.py
	python tools/check_fara_w4_representation.py
	python tools/check_fara_w5_invariance.py

.PHONY: fara-vocabulary-check
fara-vocabulary-check:
	python tools/check_fara_vocabulary_sufficiency.py
	python -m unittest tests.test_fara_vocabulary_sufficiency -v

.PHONY: fara-core-formalization-check
fara-core-formalization-check:
	python tools/check_fara_core_formalization.py
	python -m unittest tests.test_fara_core_formalization -v

.PHONY: fara-foundation-comparison-check
fara-foundation-comparison-check:
	python tools/check_fara_foundation_comparison.py
	python -m unittest tests.test_fara_foundation_comparison -v

fara-expanded-check:
	python tools/check_fara_expanded_campaign.py

.PHONY: pca-w5-check
pca-w5-check:
	python tools/check_pca_w5_approximation_cost.py
	python -m unittest tests.test_pca_w5_approximation_cost -v

.PHONY: pca-w6-check
pca-w6-check:
	python tools/check_pca_w4_domain_contracts.py
	python -m unittest tests.test_pca_w6_empirical_audit_utility -v
	python tools/check_pca_w6_empirical_audit_utility.py
