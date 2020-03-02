import nltk
from word_transformations import WordLists
from recipeFetcher import RecipeFetcher

from fractions import Fraction

STOP_WORDS = {
  'ingredients': ['taste', 'tastes']
}

PASS_WORDS = {
  'ingredients': []
}

WL = WordLists()


class WordTagger:
  def __init__(self):
    self.measurements = WL.get_words('measurements')
    self.tools = WL.get_words('tools')
    self.times = ["minutes", "seconds", "hours", "days"]
    self.methods = WL.get_words('methods')
    # store recipe data in class to access at any time
    self.found_ingredients = None
    self.found_methods = None
    self.found_tools = None

  def process_ingredients(self, recipe_results):
    # todo: may need to limit list of ingredients
    raw_ingredients = recipe_results['ingredients']
    processed_ingredients = {}

    for ing in raw_ingredients:
      ingredient_info = {
        'ingredient': '',
        'qty': 0,
        'measurement': '',
        'weight': '',
        'descrip': '',
        'paren': '',  # todo change this
      }

      split_words = ing.split()

      for fragment in split_words:
        # get the quantity from the recipe
        if '/' in fragment and '(' not in fragment:
          ingredient_info['qty'] = float(sum(Fraction(s) for s in fragment.split()))
        else:
          try:
            ingredient_info['qty'] = float(fragment)
          except ValueError:
            pass

        # get measurement from recipe
        if fragment in self.measurements:
          ingredient_info['measurement'] = fragment

        if '(' in fragment:
          split_ingredient_fragments = ing.split()
          ing_ind = split_ingredient_fragments.index(fragment)
          ing_ind_2 = ''
          if ')' in split_ingredient_fragments[ing_ind + 1]:
            ing_ind_2 = ing_ind + 1
          if ing_ind_2 == ing_ind + 1:
            ingredient_info['paren'] = ' '.join(str(m) for m in split_ingredient_fragments[ing_ind:ing_ind_2 + 1])

        # get the ingredients and description
        qty_check = fragment != ingredient_info['qty'] and not fragment.isdigit()
        msr_check = fragment != ingredient_info['measurement'] and fragment not in self.measurements \
                    and fragment + 's' not in self.measurements
        parens_check = '(' not in fragment or ')' not in fragment
        if qty_check and msr_check and parens_check:
          # use nltk to tag the parts of speach
          tagged_tokens = nltk.pos_tag(fragment.split())
          fragment_word = tagged_tokens[0][0]
          fragment_pos = tagged_tokens[0][1]

          # todo: move these codes to constants
          # assign ingredient and description based on fragment
          if fragment_word not in STOP_WORDS and (fragment_pos in ["NN", "NNS"] or fragment_word in PASS_WORDS):
            ingredient_info['ingredient'] += f'{fragment} '

          if fragment_word not in ingredient_info['ingredient'] and fragment_pos in ["JJ", "VBN", "RB"]:
            ingredient_info['descrip'] += f'{fragment} '

        # todo: maybe remove this
        if ingredient_info['qty'] == 0:
          ingredient_info['qty'] = ""

      processed_ingredients[ing] = ingredient_info

    self.found_ingredients = processed_ingredients
    return processed_ingredients

  def process_tools(self, recipe_results):
    raw_directions = recipe_results['directions']
    processed_tools = []

    for direction in raw_directions:
      for word in direction.split():
        cleaned_word = word.strip(',.').lower()
        if cleaned_word not in processed_tools and (cleaned_word in self.tools or f'{cleaned_word}s' in self.tools):
          processed_tools.append(cleaned_word)

    self.found_tools = processed_tools
    return processed_tools

  def process_recipe_methods(self, recipe_results):
    raw_directions = recipe_results['directions']
    processed_methods = []
    # todo: optimize redundant code.
    for direction in raw_directions:
      for word in direction.split():
        cleaned_word = word.strip(',.').lower()
        if cleaned_word not in processed_methods and (
            cleaned_word in self.methods or f'{cleaned_word}ing' in self.methods):
          processed_methods.append(cleaned_word)

    self.found_methods = processed_methods
    return processed_methods

  def process_directions(self, recipe_results):
    raw_directions = recipe_results['directions']
    direction_list = []
    found_directions = {}
    processed_directions = {}
    cnt = 1
    # todo: differentiate between extra (you might like) recipes and directions
    for direction in raw_directions:
      if len(direction.split()) > 2:
        split_direction = direction.split('.')
        new_direction = [chunk for chunk in split_direction if len(chunk) > 0]
        direction_list.extend(new_direction)

    for direction in raw_directions:
      cleaned_direction = direction.lower().split()
      if len(cleaned_direction) > 2:
        direction_name = f"direction_{cnt}"
        found_directions.update({direction_name:
                                   {"ingredients": [],
                                    "methods": [],
                                    "times": [],
                                    "tools": []
                                    }})

        for ind in range(len(cleaned_direction)):
          # todo: maybe don't modify the main cleaned_direction variable
          cleaned_direction[ind] = cleaned_direction[ind].strip(',.')
          for ingredient in self.found_ingredients:
            split_ingredient = ingredient.split()
            # todo: move this to a helper function to cut down on code
            ingredient_check = cleaned_direction[ind] in split_ingredient and f'{cleaned_direction[ind]}s' in \
                               split_ingredient or cleaned_direction[ind][:-1] in split_ingredient
            ing_check = cleaned_direction[ind] not in found_directions[direction_name]["ingredients"]
            # add ingredient to found directions for specific direction
            if ingredient_check and ing_check:
              found_directions[direction_name]["ingredients"].append(cleaned_direction[ind])
          # todo: maybe change to elif
          # add tools to found directions for specific direction
          tool_check = cleaned_direction[ind] in self.found_tools or f'{cleaned_direction[ind]}s' in \
                       self.found_tools or cleaned_direction[ind][:-1] in self.found_tools
          t_check = cleaned_direction[ind] not in found_directions[direction_name]['tools']
          if tool_check and t_check:
            found_directions[direction_name]["tools"].append(cleaned_direction[ind])

          # add methods to found directions for specific direction
          method_check = cleaned_direction[ind] in self.found_methods or f'{cleaned_direction[ind]}s' in \
                         self.found_methods or cleaned_direction[ind][:-1] in self.found_tools
          m_check = cleaned_direction[ind] not in found_directions[direction_name]['methods']
          if method_check and m_check:
            found_directions[direction_name]["methods"].append(cleaned_direction[ind])

          # add timing
          timing_done = False
          # TIMING METHOD 1
          if cleaned_direction[ind] == 'degrees':
            cln_degrees = []
            if cleaned_direction[ind - 1].strip('()').isdigit():
              cln_degrees.append(cleaned_direction[ind - 1])
            if len(cleaned_direction[ind+1].strip("().")) == 1:
              cln_degrees.append(cleaned_direction[ind + 1])

            deg_str = ' DEGREES '.join(cln_degrees).strip("().")
            found_directions[direction_name]["times"].append(deg_str)
            timing_done = True

          # TIMING METHOD 2
          time_check = cleaned_direction[ind] in self.times or f'{cleaned_direction[ind]}s' in \
                         self.times or cleaned_direction[ind][:-1] in self.times
          tm_check = cleaned_direction[ind] not in found_directions[direction_name]['times']
          if not timing_done and time_check and tm_check:
            temp_count = 1
            temp_str = cleaned_direction[ind]
            while True:
              if cleaned_direction[ind - temp_count].isdigit() or cleaned_direction[ind - temp_count] == "to":
                temp_str = cleaned_direction[ind - temp_count] + " " + temp_str
              else:
                break
              temp_count += 1
              found_directions[direction_name]["times"].append(temp_str)

          cnt += 1

    processed_directions.update({"raw": direction_list})
    processed_directions.update({"cleaned": found_directions})
    return processed_directions

if __name__ == '__main__':
  rf = RecipeFetcher()
  meat_lasagna = rf.search_recipes('meat lasagna')[0]
  recipe = rf.scrape_recipe(meat_lasagna)
  tagger = WordTagger()
  tagger.process_ingredients(recipe)
  tagger.process_tools(recipe)
  tagger.process_recipe_methods(recipe)
  tagger.process_directions(recipe)

