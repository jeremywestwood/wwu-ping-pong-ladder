wwu-ping-pong-ladder
====================

A simple ping pong ladder using the python trueskill module to rank opponents.

Setting up to run from git
--------------------------

git submodule init  
git submodule update  
pip install -r requirements.txt

Running server from git
-----------------------

python pingpongladder.py

Accessing the web interface
---------------------------

Listens on http://localhost:8080/

Adding users to database
------------------------

sqlite3 data/pingpongladder.db  
insert into users (permission_level, username, displayname, email, showemail) values(1, 'pingp', 'Mr Ping Pong', 'pingp@gmail.com', 0);

