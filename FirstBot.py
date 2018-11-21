import hlt  #main halite stuff
from hlt import constants  # halite constants
from hlt.positionals import Direction, Position  # helper for moving
import random  # randomly picking a choice for now.
import logging  # logging stuff to console
import math
import pandas as pd

game = hlt.Game()  # game object
# Initializes the game
game.ready("FirstBot")

ship_states = {}

all_positions_halite = {}
max_height = game.game_map.height
max_width = game.game_map.width
#print(f'Game map is a {max_height}x{max_width}')
# going to try to iterate through every position on the map and grab the halite amount
# once we store that in a dictionary, we can begin game planning for where to build shipyards

'''
game_map = game.game_map

for x in range(max_width):
    for y in range(max_height):
        tmp_position = Position(x, y)
        print(f'tmp_position - {tmp_position}')
        halite_amount = game_map[tmp_position].halite_amount
        print(f'halite - {halite_amount}')
        #all_positions_halite[tmp_position] = halite_amount
        all_positions_halite[f'{x}-{y}'] = halite_amount

print('\n\nLoop finished\n\n')
df = pd.DataFrame(all_positions_halite.items()).reset_index()
df.columns = ['Position', 'Halite']
df.to_csv('./data/halite.csv')
'''

x = 0
y = 0



while True:
    # This loop handles each turn of the game. The game object changes every turn, and you refresh that state by
    game.update_frame()

    # You extract player metadata and the updated map metadata here for convenience.
    me = game.me

    '''comes from game, game comes from before the loop, hlt.Game points to networking, which is where you will
    find the actual Game class (hlt/networking.py). From here, GameMap is imported from hlt/game_map.py.

    open that file to seee all the things we do with game map.'''
    game_map = game.game_map  # game map data. Recall game is

    max_height = game.game_map.height
    for y in range(max_height):
        tmp_position = Position(x, y)
        #print(f'tmp_position - {tmp_position}')
        halite_amount = game_map[tmp_position].halite_amount
        #print(f'halite - {halite_amount}')
        #all_positions_halite[tmp_position] = halite_amount
        all_positions_halite[f'{x} {y}'] = halite_amount

    if x == game.game_map.width - 1:
        df = pd.DataFrame.from_dict(all_positions_halite, orient='index')
        df.reset_index(inplace=True)
        df.columns = ['Position', 'Halite']

        df['x'] = df['Position'].str.split(' ', 1).str[0]
        df['y'] = df['Position'].str.split(' ', 1).str[1]

        df.drop('Position', axis=1, inplace=True)

        df.to_csv('./data/halite.csv', index=False)

    # A command queue holds all the commands you will run this turn. You build this list up and submit it at the
    #   end of the turn.
    command_queue = []

    # specify the order we know this all to be
    direction_order = [Direction.North, Direction.South, Direction.East, Direction.West, Direction.Still]

    position_choices = []
    for ship in me.get_ships():
        if ship.id not in ship_states:
            ship_states[ship.id] = "collecting"

        if ship_states[ship.id] == "collecting":
            # cardinals get surrounding cardinals using get_all_cardinals in positionals.py.
            # reading this file, I can see they will be in order of:
            # [Direction.North, Direction.South, Direction.East, Direction.West]

            # maps with position orders, but also gives us all the surrounding possitions
            position_options = ship.position.get_surrounding_cardinals() + [ship.position]

            # we will be mapping the "direction" to the actual position

            # position_dict = {(0, -1): Position(8, 15), (0, 1): Position(8, 17), (1, 0): Position(9, 16), (-1, 0): Position(7, 16), (0, 0): Position(8, 16)}
            position_dict = {}

            # maps the direction choice with halite
            # halite_dict = {(0, -1): 708, (0, 1): 492, (1, 0): 727, (-1, 0): 472, (0, 0): 0}
            halite_dict = {}

            for n, direction in enumerate(direction_order):
                position_dict[direction] = position_options[n]

            for direction in position_dict:
                position = position_dict[direction]
                halite_amount = game_map[position].halite_amount
                if position_dict[direction] not in position_choices:
                    if direction == Direction.Still:
                        halite_amount *= 4
                    halite_dict[direction] = halite_amount

            directional_choice = max(halite_dict, key=halite_dict.get)
            position_choices.append(position_dict[directional_choice])

            command_queue.append(ship.move(game_map.naive_navigate(ship, ship.position+Position(*directional_choice))))

            if ship.halite_amount >= constants.MAX_HALITE * 0.75:
                ship_states[ship.id] = "depositing"

        elif ship_states[ship.id] == "depositing":
            move = game_map.naive_navigate(ship, me.shipyard.position)
            upcoming_position = ship.position + Position(*move)
            if upcoming_position not in position_choices:
                position_choices.append(upcoming_position)
                command_queue.append(ship.move(move))
                if move == Direction.Still:
                    ship_states[ship.id] = "collecting"
            else:
                position_choices.append(ship.position)
                command_queue.append(ship.move(game_map.naive_navigate(ship, ship.position+Position(*Direction.Still))))

    # ship costs 1000, dont make a ship on a ship or they both sink
    if len(me.get_ships()) < math.ceil(game.turn_number / 25):
        if me.halite_amount >= 1000 and not game_map[me.shipyard].is_occupied:
            command_queue.append(me.shipyard.spawn())


    # increasing x so that we can continue to capture the next column of data and halite
    x += 1

    # Send your moves back to the game environment, ending this turn.
    game.end_turn(command_queue)