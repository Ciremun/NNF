CREATE TABLE IF NOT EXISTS 
users(id serial primary key, username text, displayname text, password text, usertype text, date date);

CREATE TABLE IF NOT EXISTS 
sessions(id serial primary key, sid text, username text, usertype text, date date);

CREATE TABLE IF NOT EXISTS 
dailymenu(id serial primary key, title text, weight text, calories text, price integer, 
link text, image_link text, section text, type text, date date);

CREATE TABLE IF NOT EXISTS 
cart(user_id integer references users(id), id serial primary key);

CREATE TABLE IF NOT EXISTS 
cartproduct(cart_id integer references cart(id), 
product_id integer references dailymenu(id), amount integer, id serial primary key);

CREATE TABLE IF NOT EXISTS 
orders(user_id integer references users(id), id serial primary key);

CREATE TABLE IF NOT EXISTS 
orderproduct(order_id integer references orders(id), 
title text, price integer, link text, amount integer, id serial primary key);