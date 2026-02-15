import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
from nltk.probability import FreqDist
from nltk import pos_tag, ne_chunk
from nltk.tree import Tree

# Ensure necessary NLTK resources are downloaded
nltk.download('punkt')
nltk.download('stopwords')
nltk.download('averaged_perceptron_tagger')
nltk.download('maxent_ne_chunker')
nltk.download('words')

class Script:
    def __init__(self, user_input):
        self.user_input = user_input

    def generate_script(self):
        try:
            sentences = sent_tokenize(self.user_input)
            words = word_tokenize(self.user_input)
            words = [word.lower() for word in words if word.isalnum()]
            stop_words = set(stopwords.words('english'))
            filtered_words = [word for word in words if word not in stop_words]

            # Frequency distribution of words
            freq_dist = FreqDist(filtered_words)

            # Part of Speech Tagging
            pos_tags = pos_tag(filtered_words)

            # Named Entity Recognition
            named_entities = ne_chunk(pos_tags)
            entities = self.extract_entities(named_entities)

            # Constructing the script content
            script_content = {
                "sentences": sentences,
                "word_frequency": freq_dist.most_common(10),
                "entities": entities
            }

            return script_content
        except Exception as e:
            print(f"Error generating script: {str(e)}")
            return None

    def extract_entities(self, tree):
        entities = []
        for subtree in tree:
            if isinstance(subtree, Tree):
                entity_name = " ".join([leaf[0] for leaf in subtree.leaves()])
                entity_type = subtree.label()
                entities.append((entity_name, entity_type))
        return entities