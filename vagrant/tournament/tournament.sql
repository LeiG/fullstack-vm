-- Table definitions for the tournament project.
--
-- Put your SQL 'create table' statements in this file; also 'create view'
-- statements if you choose to use it.
--
-- You can write comments in this file by starting them with two dashes, like
-- these lines here.

DROP DATABASE IF EXISTS tournament;

CREATE DATABASE tournament;
\c tournament;

CREATE TABLE players(
  id    SERIAL  UNIQUE PRIMARY KEY,
  name  TEXT    NOT NULL
);

CREATE TABLE matches(
  id         SERIAL  UNIQUE PRIMARY KEY,
  winner_id  INT     NOT NULL,
  loser_id   INT     NOT NULL
);

CREATE VIEW win AS
  SELECT
    players.id AS id,
    MIN(players.name) AS name,
    SUM(CASE WHEN matches.winner_id IS NOT NULL THEN 1 ELSE 0 END) AS wins
  FROM matches
  FULL OUTER JOIN players
  ON players.id = matches.winner_id
  GROUP BY players.id;

CREATE VIEW loss AS
  SELECT
    players.id AS id,
    MIN(players.name) AS name,
    SUM(CASE WHEN matches.loser_id IS NOT NULL THEN 1 ELSE 0 END) AS losses
  FROM matches
  FULL OUTER JOIN players
  ON players.id = matches.loser_id
  GROUP BY players.id;

CREATE VIEW standings AS
  SELECT
    win.id AS id,
    win.name AS name,
    win.wins AS wins,
    win.wins + loss.losses AS matches
  FROM win
  JOIN loss
  ON win.id = loss.id
