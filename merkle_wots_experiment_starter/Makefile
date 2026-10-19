.PHONY: test quick full state
test:
	python -m unittest discover -s tests -v
quick:
	python experiments/benchmark_endpoint_modes.py --trees 3 --leaves 5 --repeats 5 --warmups 10 --out results/quick.csv
	python experiments/analyze_paired.py results/quick.csv --out results/quick_summary.json
state:
	python experiments/state_allocator_stress.py --workers 8 --per-worker 100 --db results/state_test.sqlite
full:
	python experiments/benchmark_endpoint_modes.py --trees 20 --leaves 15 --repeats 30 --warmups 100 --out results/endpoint_raw.csv
	python experiments/analyze_paired.py results/endpoint_raw.csv --out results/endpoint_summary.json
	python experiments/state_allocator_stress.py --workers 8 --per-worker 100 --db results/state_test.sqlite
