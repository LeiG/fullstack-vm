#!/usr/bin/env python

import psycopg2


def connect():
    """Connect to the PG database - news

    Returns
      database connection
    """
    conn = psycopg2.connect("dbname=news")
    cur = conn.cursor()
    return conn, cur


class Database():
    def __init__(self):
        self.conn, self.cur = connect()

    def __enter__(self):
        return self.cur

    def __exit__(self, type, value, traceback):
        self.conn.commit()
        self.conn.close()


def getMostPopularArticles(n=3):
    """Get n most popular articles of all time

    Returns
      - title
      - number of page views
    """
    database = Database()

    query = """
    WITH most_viewed_articles AS (
      SELECT
        COUNT(*) AS views,
        replace(path, '/article/', '') AS slug
      FROM
        log
      WHERE
        path LIKE '/article/%%'
      GROUP BY path
      ORDER BY views DESC
      LIMIT %s
    )

    SELECT
      a.title AS title,
      CAST(m.views AS INT) AS views
    FROM
      most_viewed_articles m
    JOIN
      articles a
    ON m.slug = a.slug
    ORDER BY 2 DESC
    """

    with database as db:
        db.execute(query, (n,))
        articles = list(db.fetchall())

    return articles


def getMostPopularArticleAuthors(n=4):
    """Get n most popular article authors of all time

    Return
      - author
      - number of page views
    """
    database = Database()

    query = """
    WITH article_views AS (
      SELECT
        COUNT(*) AS views,
        replace(path, '/article/', '') AS slug
      FROM
        log
      WHERE
        path LIKE '/article/%%'
      GROUP BY path
    ),

    most_viewed_authors AS (
      SELECT
        a.author AS author,
        CAST(SUM(v.views) AS INT) AS views
      FROM
        article_views v
      JOIN
        articles a
      ON v.slug = a.slug
      GROUP BY a.author
      ORDER BY 2 DESC
      LIMIT %s
    )

    SELECT
      a.name AS author,
      m.views AS views
    FROM
      most_viewed_authors m
    JOIN
      authors a
    ON m.author = a.id
    ORDER BY 2 DESC
    """

    with database as db:
        db.execute(query, (n,))
        authors = list(db.fetchall())

    return authors


def getDatesWithHighErrorRate(error_rate=0.01):
    """Get all days with error rate higher than error_rate

    Return
      - date
      - error rate
    """
    database = Database()

    query = """
    SELECT
      to_char(date(time), 'YYYY-MM-DD') AS event_date,
      CAST(SUM(CASE WHEN status LIKE '404%%' THEN 1 ELSE 0 END) AS FLOAT)
        / CAST(COUNT(*) AS FLOAT) * 100 AS err_rate
    FROM log
    GROUP BY date(time)
    HAVING CAST(SUM(CASE WHEN status LIKE '404%%' THEN 1 ELSE 0 END) AS FLOAT)
             / CAST(COUNT(*) AS FLOAT) > %s
    ORDER BY 2 DESC
    """

    with database as db:
        db.execute(query, (error_rate,))
        dates = list(db.fetchall())

    return dates


if __name__ == "__main__":
    popular_articles = getMostPopularArticles(3)

    print("===Top 3 Most Popular Articles===")
    print(popular_articles)
    print("\n")

    popular_article_authors = getMostPopularArticleAuthors(4)

    print("===Top 4 Most Popular Article Authors===")
    print(popular_article_authors)
    print("\n")

    high_error_rate_dates = getDatesWithHighErrorRate(0.01)

    print("===Dates with Error Rate > 1%===")
    print(high_error_rate_dates)
    print("\n")
