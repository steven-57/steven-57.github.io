import os
import tqdm

chunk_size = 20 * 1024 * 1024


def get_targets():
    l = os.listdir("sources")
    return [os.path.splitext(f)[0] for f in l if os.path.splitext(f)[-1] == ".json"]


def do_split():
    targets = get_targets()
    if not os.path.isdir("sources/fragments"):
        os.makedirs("sources/fragments")
    for target in tqdm.tqdm(targets):
        source_path = os.path.join("sources", f"{target}.docx")
        fragment_path = os.path.join("sources", "fragments", f"{target}")
        if not os.path.isfile(source_path):
            print(f"Source file {source_path} does not exist.")
            continue
        if not os.path.isdir(fragment_path):
            os.makedirs(fragment_path)
        with open(source_path, 'rb') as source_file:
            index = 0
            while True:
                chunk = source_file.read(chunk_size)
                if not chunk:
                    break
                fragment_file_path = os.path.join(fragment_path, f"{index}.part")
                with open(fragment_file_path, 'wb') as fragment_file:
                    fragment_file.write(chunk)
                index += 1


def do_merge():
    targets = get_targets()
    for target in tqdm.tqdm(targets):
        source_path = os.path.join("sources", f"{target}.docx")
        fragment_path = os.path.join("sources", "fragments", f"{target}")
        if os.path.isfile(source_path):
            print(f"Source file {source_path} already exists. Skipping merge.")
            continue
        if not os.path.isdir(fragment_path):
            print(f"Fragment directory {fragment_path} does not exist.")
            continue
        fragments = [f for f in os.listdir(fragment_path) if f.endswith(".part")]
        fragments.sort(key=lambda x: int(x.split('.')[0]))
        for fragment in fragments:
            fragment_file_path = os.path.join(fragment_path, fragment)
            with open(fragment_file_path, 'rb') as fragment_file:
                with open(source_path, 'ab') as source_file:
                    source_file.write(fragment_file.read())


def main():
    op = input("what operation do you want to perform? (1: split, 2: merge): ").strip()
    if op == "1":
        do_split()
    elif op == "2":
        do_merge()
    else:
        print("Invalid operation. Please choose 1 for split or 2 for merge.")
        main()
    input("Press Enter to exit...")


if __name__ == "__main__":
    main()
