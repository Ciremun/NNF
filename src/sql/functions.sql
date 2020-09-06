CREATE OR REPLACE FUNCTION addUser(uName text, dName text, pass text, uType text, regDate timestamp)
    RETURNS users.id%TYPE AS $$
    DECLARE newid users.id%TYPE;
    BEGIN
        INSERT INTO users(username, displayname, password, usertype, date)
            VALUES (uName, dName, pass, uType, regDate) RETURNING id INTO newid;
        INSERT INTO cart(user_id) VALUES (newid);
        RETURN newid;
    END;
    $$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION addCartProduct(cID int, pID int, pAmount int, dateAdded timestamp)
    RETURNS VOID AS $$
    BEGIN
        IF (SELECT EXISTS(SELECT 1 FROM cartproduct WHERE cart_id = cID AND product_id = pID)) THEN
            UPDATE cartproduct SET amount = amount + pAmount 
                WHERE cart_id = cID AND product_id = pID;
        ELSE
            INSERT INTO cartproduct(cart_id, product_id, amount, date) 
                VALUES (cID, pID, pAmount, dateAdded);
        END IF;
    END;
    $$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION updateCartProduct(cID int, pID int, pAmount int)
    RETURNS VOID as $$
    BEGIN
        IF (pAmount = 0) THEN
            DELETE FROM cartproduct WHERE cart_id = cID AND product_id = pID;
        ELSE
            UPDATE cartproduct SET amount = pAmount WHERE cart_id = cID AND product_id = pID;
        END IF;
    END;
    $$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION addAccountShare(userID int, targetUserID int, shareDuration interval, dateAdded timestamp)
    RETURNS VOID AS $$
    BEGIN
        IF (SELECT EXISTS(SELECT 1 FROM account_share WHERE user_id = userID AND target_user_id = targetUserID)) THEN
            UPDATE account_share SET duration = shareDuration, date = dateAdded 
                WHERE user_id = userID AND target_user_id = targetUserID;
        ELSE
            INSERT INTO account_share(user_id, target_user_id, duration, date) 
                VALUES (userID, targetUserID, shareDuration, dateAdded);
        END IF;
    END;
    $$ LANGUAGE plpgsql;

