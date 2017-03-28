#!/usr/bin/env python
#
# tournament.py -- implementation of a Swiss-system tournament
#

import psycopg2


def connect():
    """Connect to the PostgreSQL database.  Returns a database connection."""
    conn = psycopg2.connect("dbname=tournament")
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


def deleteMatches():
    """Remove all the match records from the database."""
    database = Database()

    with database as db:
        db.execute("TRUNCATE matches RESTART IDENTITY CASCADE;")


def deletePlayers():
    """Remove all the player records from the database."""
    database = Database()

    with database as db:
        db.execute("TRUNCATE players RESTART IDENTITY CASCADE;")


def countPlayers():
    """Returns the number of players currently registered."""
    database = Database()

    with database as db:
        db.execute("SELECT COUNT(*) FROM players;")
        numPlayers = db.fetchone()[0]

    return numPlayers


def registerPlayer(name):
    """Adds a player to the tournament database.

    The database assigns a unique serial id number for the player.  (This
    should be handled by your SQL database schema, not in your Python code.)

    Args:
      name: the player's full name (need not be unique).
    """
    database = Database()

    with database as db:
        query = "INSERT INTO players (id, name) VALUES (DEFAULT, %s)"
        params = (name,)
        db.execute(query, params)


def playerStandings():
    """Returns a list of the players and their win records, sorted by wins.

    The first entry in the list should be the player in first place, or a
    player tied for first place if there is currently a tie.

    Returns:
      A list of tuples, each of which contains (id, name, wins, matches):
        id: the player's unique id (assigned by the database)
        name: the player's full name (as registered)
        wins: the number of matches the player has won
        matches: the number of matches the player has played
    """
    database = Database()

    with database as db:
        db.execute("SELECT * FROM standings ORDER BY wins DESC;")
        standings = db.fetchall()

    return standings


def reportMatch(winner, loser):
    """Records the outcome of a single match between two players.

    Args:
      winner:  the id number of the player who won
      loser:  the id number of the player who lost
    """
    database = Database()

    with database as db:
        query = """
        INSERT INTO matches (id, winner_id, loser_id) VALUES (DEFAULT, %s, %s)
        """
        params = (winner, loser)
        db.execute(query, params)


def swissPairings():
    """Returns a list of pairs of players for the next round of a match.

    Assuming that there are an even number of players registered, each player
    appears exactly once in the pairings.  Each player is paired with another
    player with an equal or nearly-equal win record, that is, a player adjacent
    to him or her in the standings.

    Returns:
      A list of tuples, each of which contains (id1, name1, id2, name2)
        id1: the first player's unique id
        name1: the first player's name
        id2: the second player's unique id
        name2: the second player's name
    """
    player_standings = playerStandings()

    database = Database()

    with database as db:
        db.execute("SELECT winner_id, loser_id FROM matches;")
        matches = set(db.fetchall())

    pairings = []
    while len(player_standings) > 0:
        candidate_a = player_standings.pop(0)
        for candidate_b in player_standings:
            if (candidate_a, candidate_b) not in matches\
               and (candidate_b, candidate_a) not in matches:
                pairings.append(
                    (
                        candidate_a[0],
                        candidate_a[1],
                        candidate_b[0],
                        candidate_b[1],
                    )
                )
                player_standings.remove(candidate_b)
                break

    return pairings
