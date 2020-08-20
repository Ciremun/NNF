CREATE TABLE IF NOT EXISTS 
users(id serial primary key, username text, displayname text, password text, usertype text, date date);

CREATE TABLE IF NOT EXISTS 
sessions(id serial primary key, sid text, username text, usertype text, date date, 
user_id integer references users(id) on delete cascade);

CREATE TABLE IF NOT EXISTS 
dailymenu(id serial primary key, title text, weight text, calories text, price integer, 
link text, image_link text, section text, type text, date date);

CREATE TABLE IF NOT EXISTS 
cart(user_id integer references users(id) on delete cascade, id serial primary key);

CREATE TABLE IF NOT EXISTS 
cartproduct(cart_id integer references cart(id) on delete cascade, 
product_id integer references dailymenu(id) on delete cascade, amount integer, date float, id serial primary key);

CREATE TABLE IF NOT EXISTS 
orders(user_id integer references users(id) on delete cascade, id serial primary key);

CREATE TABLE IF NOT EXISTS 
orderproduct(order_id integer references orders(id) on delete cascade, 
title text, price integer, link text, amount integer, id serial primary key);

CREATE TABLE IF NOT EXISTS 
account_share(user_id integer references users(id) on delete cascade, 
target_user_id integer references users(id) on delete cascade, duration float, date float, id serial primary key);
