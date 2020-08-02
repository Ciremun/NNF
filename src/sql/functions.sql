CREATE OR REPLACE FUNCTION addUser(text, text, text, text, date)
    RETURNS VOID AS $$
    DECLARE newid users.id%TYPE;
    BEGIN
        INSERT INTO users(username, displayname, password, usertype, date)
            VALUES ($1, $2, $3, $4, $5) RETURNING id INTO newid;
        INSERT INTO cart(user_id) VALUES (newid);

    END;
    $$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION deleteCart()
    RETURNS TRIGGER AS $$
    BEGIN
        DELETE FROM cartproduct
            WHERE cart_id = (SELECT id FROM cart WHERE user_id = OLD.id);
        DELETE FROM cart
            WHERE user_id = OLD.id;
        RETURN OLD;
    END;
    $$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION deleteCartProduct()
    RETURNS TRIGGER AS $$
    BEGIN
        DELETE FROM cartproduct
            WHERE product_id = OLD.id;
        RETURN OLD;
    END;
    $$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION deleteOrders()
    RETURNS TRIGGER AS $$
    BEGIN
        DELETE FROM orderproduct
            WHERE order_id = (SELECT id FROM orders WHERE user_id = OLD.id);
        DELETE FROM orders
            WHERE user_id = OLD.id;
        RETURN OLD;
    END;
    $$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION addCartProduct(int, int, int)
    RETURNS VOID AS $$
    BEGIN
        IF (SELECT EXISTS(SELECT 1 FROM cartproduct WHERE cart_id = $1 AND product_id = $2)) THEN
            UPDATE cartproduct SET amount = amount + $3 WHERE cart_id = $1 AND product_id = $2;
        ELSE
            INSERT INTO cartproduct(cart_id, product_id, amount) VALUES ($1, $2, $3);
        END IF;
    END;
    $$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS deleteCartTrigger on users;
DROP TRIGGER IF EXISTS deleteCartProductTrigger on dailymenu;
DROP TRIGGER IF EXISTS deleteOrdersTrigger on users;

CREATE TRIGGER deleteCartTrigger
    BEFORE DELETE ON users
    FOR EACH ROW
    EXECUTE FUNCTION deleteCart();

CREATE TRIGGER deleteCartProductTrigger
    BEFORE DELETE ON dailymenu
    FOR EACH ROW
    EXECUTE FUNCTION deleteCartProduct();

CREATE TRIGGER deleteOrdersTrigger
    BEFORE DELETE ON users
    FOR EACH ROW
    EXECUTE FUNCTION deleteOrders();