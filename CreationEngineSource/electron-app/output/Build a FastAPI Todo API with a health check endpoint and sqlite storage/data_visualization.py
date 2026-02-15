import matplotlib.pyplot as plt
from error_handling import handle_error

def visualize_data(data):
    """
    Visualizes the given data using Matplotlib.

    :param data: The data to visualize. Expected to be a dictionary with keys as labels and values as data points.
    """
    try:
        if not isinstance(data, dict):
            raise ValueError("Data must be a dictionary with labels as keys and data points as values.")

        labels = list(data.keys())
        values = list(data.values())

        plt.figure(figsize=(10, 5))
        plt.bar(labels, values, color='skyblue')
        plt.xlabel('Labels')
        plt.ylabel('Values')
        plt.title('Data Visualization')
        plt.xticks(rotation=45)
        plt.tight_layout()

        plt.show()

    except Exception as e:
        handle_error(e)