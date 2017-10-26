run with: 

vegeta attack -rate=50 -targets=targets.txt > results.bin
vegeta report -inputs=results.bin -reporter=json > metrics.json
cat results.bin | vegeta report -reporter=plot > plot.html


INFO: remove rate limiting in nginx.conf when running tests!
