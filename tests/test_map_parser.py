from core.parsers.map_parser import parse_entities


def test_parse_single_entity():
    content = """\
{
"classname" "light"
"origin" "128 256 64"
"light" "300"
}
"""
    entities = parse_entities(content)
    assert len(entities) == 1
    assert entities[0].classname == "light"
    assert entities[0].properties["origin"] == "128 256 64"
    assert entities[0].properties["light"] == "300"


def test_parse_entity_with_brushes():
    content = """\
{
"classname" "worldspawn"
{
( 0 0 0 ) ( 64 0 0 ) ( 0 64 0 ) texture 0 0 0 1 1
( 0 0 0 ) ( 0 0 64 ) ( 64 0 0 ) texture 0 0 0 1 1
}
}
{
"classname" "light"
"origin" "0 0 0"
}
"""
    entities = parse_entities(content)
    assert len(entities) == 2
    assert entities[0].classname == "worldspawn"
    assert entities[1].classname == "light"


def test_parse_multiple_entities():
    content = """\
{
"classname" "worldspawn"
}
{
"classname" "info_player_start"
"origin" "0 0 24"
}
{
"classname" "monster_ogre"
"origin" "256 128 0"
"angle" "90"
}
"""
    entities = parse_entities(content)
    assert len(entities) == 3


def test_parse_empty():
    assert parse_entities("") == []


def test_entity_without_classname():
    content = """\
{
"origin" "0 0 0"
}
"""
    entities = parse_entities(content)
    assert len(entities) == 1
    assert entities[0].classname == ""
