#!/usr/bin/env python3
import nets
import tiles
import pytrellis
import database
import re

# Experiments building a compressed routing graph

# Nets are a three-tuple ((rel_rows, rel_cols), netname) for normal nets or ("G", "netname") for globals
# Arcs are a tuple (source, dest, configurable, loc) of netnames (loc is relative position to tile containing switch

# We combine all tiles at a given location into one "tiles" entry
# Tiles entries are a tuple (nets, arcs) of sets



def main():
    tiles = []

    pytrellis.load_database(database.get_db_root())
    c = pytrellis.Chip("LFE5U-45F")
    max_row = c.get_max_row()
    max_col = c.get_max_col()
    # Init tile structure
    for row in range(max_row+1):
        tiles.append([])
        for col in range(max_col+1):
            tiles[row].append((set(), set()))

    rel_netname_re = re.compile(r'([NS]\d+)?([EW]\d+)?_')
    netids = {}

    def parse_netname(netname, curr_tile, dest_tile):
        if netname.startswith("G_") or netname.startswith("L_") or netname.startswith("R_"):
            return "G", netname[2:]
        elif netname.startswith("BNK_") or netname.startswith("DQSG_"):
            return None  # TODO
        m = rel_netname_re.match(netname)
        wire_pos = curr_tile
        if m:
            for g in m.groups():
                if g is not None:
                    delta = int(g[1:])
                    if g[0] == "N":
                        wire_pos = (wire_pos[0] - delta, wire_pos[1])
                    elif g[0] == "S":
                        wire_pos = (wire_pos[0] + delta, wire_pos[1])
                    elif g[0] == "W":
                        wire_pos = (wire_pos[0], wire_pos[1] - delta)
                    elif g[0] == "E":
                        wire_pos = (wire_pos[0], wire_pos[1] + delta)
            netname = netname.split("_", 1)[1]
        if netname in netids:
            netid = netids[netname]
        else:
            netid = len(netids)
            netids[netname] = netid
        return (wire_pos[0] - dest_tile[0], wire_pos[1] - dest_tile[1]), netid

    def in_bounds(pos):
        return pos[0] >= 0 and pos[0] <= max_row and pos[1] >= 0 and pos[1] <= max_col

    # Analyse connectivity
    for row in range(max_row+1):
        for col in range(max_col+1):
            print("R{}C{}".format(row, col))
            pos = row, col

            def add_net_get_pos(net):
                if net is None:
                    return None
                netpos, name = net
                if netpos == "G":
                    return None
                net_row = netpos[0] + row
                net_col = netpos[1] + col
                if in_bounds((net_row, net_col)):
                    tiles[net_row][net_col][0].add(net)
                return net_row, net_col

            def add_arc(srcname, dstname, conf):
                srcnet = parse_netname(srcname, pos, pos)
                dstnet = parse_netname(dstname, pos, pos)
                if srcnet is None or dstnet is None:
                    return
                srcpos = add_net_get_pos(srcnet)
                dstpos = add_net_get_pos(dstnet)

                # Add arc to both source and dest tiles
                if dstpos is not None and in_bounds(dstpos):
                    dstarc = (parse_netname(srcname, pos, dstpos), parse_netname(dstname, pos, dstpos), conf, (pos[0] - dstpos[0], pos[1] - dstpos[1]))
                    tiles[dstpos[0]][dstpos[1]][1].add(dstarc)
                if srcpos is not None and in_bounds(srcpos):
                    srcarc = (parse_netname(srcname, pos, srcpos), parse_netname(dstname, pos, srcpos), conf, (pos[0] - srcpos[0], pos[1] - srcpos[1]))
                    tiles[srcpos[0]][srcpos[1]][1].add(srcarc)

            for tile in c.get_tiles_by_position(row, col):
                tinf = tile.info
                tdb = pytrellis.get_tile_bitdata(pytrellis.TileLocator(c.info.family, c.info.name, tinf.type))
                for sink in tdb.get_sinks():
                    mux = tdb.get_mux_data_for_sink(sink)
                    for src in mux.get_sources():
                        add_arc(src, sink, True)

                for fc in tdb.get_fixed_conns():
                    add_arc(fc.source, fc.sink, False)

    unique_tiles = set()

    for row in range(max_row+1):
        for col in range(max_col+1):
            tilesite = tiles[row][col]
            ftilesite = frozenset(tilesite[0]), frozenset(tilesite[1])
            unique_tiles.add(ftilesite)
    tilearcs = 0
    tilenets = 0
    for ut in unique_tiles:
        tilearcs += len(ut[1])
        tilenets += len(ut[0])
    print("{} unique tiles out of {} total locations".format(len(unique_tiles), (max_row+1) * (max_col + 1)))
    print("{} net entries, {} arc entries, across all stored tiles".format(tilenets, tilearcs))
    print("{} unqiue netnames".format(len(netids)))

if __name__ == "__main__":
    main()
