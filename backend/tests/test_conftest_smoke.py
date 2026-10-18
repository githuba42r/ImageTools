import jwt as _jwt

def test_keypair_and_make_jwt(oauth2_keypair, make_jwt):
    token = make_jwt(email="x@y.z", fullname="X Y")
    claims = _jwt.decode(token, oauth2_keypair["public_pem"], algorithms=["RS256"], options={"verify_exp": False})
    assert claims["email"] == "x@y.z"
    assert claims["name"]["fullname"] == "X Y"
    assert "expires" in claims
