# Logs Analysis

This project analyze the log files given in the database `news`.

Specifically, three questions are answered

1. What are the most popular three articles of all time?
2. Who are the most popular article authors of all time?
3. On which days did more than 1% of requests lead to errors?

To run the program, you need to first set up the database via

```
$psql -d news -f newsdata.sql
```

And then run

```
$python report.py
```
