# Reproducibility entry points (reviewer round 7, item 9.2).
#
#   make test             -> fast deterministic checks (a few seconds)
#   make audit-data       -> data authenticity audit (round 9): proves the
#                            paper numbers come from a rerunnable pipeline
#   make reproduce-quick  -> deterministic audit + accounting, no fresh timing
#   make reproduce-full   -> full pipeline incl. fresh timing and figures
#
# WARNING: `make reproduce-full` reruns experiments/experiment_submission.py,
# which generates a *new* timing sample.  The paper's tables cite the retained
# authoritative sample (results_submission.json, round-3 rerun); rerunning the
# timing experiment produces fresh numbers that replace that authority.  Use
# the quick target for verification and the full target only when you intend a
# new measurement campaign.

.PHONY: test reproduce-quick reproduce-full audit-data

audit-data:
	python3 audit/data_authenticity_audit.py

test:
	python3 tests/test_encoding.py
	python3 tests/test_chain_counts.py
	python3 tests/test_serialization.py
	python3 tests/test_bip360_vectors.py
	python3 tests/test_paper_numbers.py
	python3 experiments/sync_paper_tables.py
	python3 audit/audit_jce.py
	python3 audit/state_model_jce.py
	python3 audit/state_persistence_tests.py
	python3 state_demo/test_state.py
	python3 experiments/check_counts.py
	python3 experiments/robust_stats.py
	python3 charts/render_jce.py

reproduce-quick: test

reproduce-full:
	$(MAKE) reproduce-quick
	python3 experiments/experiment_submission.py
	(cd bench/native && ./build.sh)
	python3 bench/native/run_sessions.py bench/native/_build
	python3 charts/make_submission_figure.py
	python3 charts/render_jce.py --from-markdown
