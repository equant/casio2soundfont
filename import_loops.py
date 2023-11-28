import os
import struct

def read_chunk_header(file):
    header = file.read(8)
    if len(header) < 8:
        return None, None
    chunk_id, size = struct.unpack('<4sI', header)
    #print(f"Chunk: {chunk_id}, {size}")  # Debugging print statement
    return chunk_id, size

def read_list_chunk(file, size):
    list_type = file.read(4).decode('utf-8')
    size -= 4  # Adjust the size for the read bytes

    sub_chunks = {}
    while size > 0:
        sub_chunk_id, sub_chunk_size = read_chunk_header(file)
        if sub_chunk_id is None:
            break

        # Read the sub-chunk data
        sub_chunks[sub_chunk_id] = file.read(sub_chunk_size)
        size -= 8 + sub_chunk_size

    return list_type, sub_chunks

def read_sf2(file_path):
    sf2_data = {'chunks': []}
    with open(file_path, 'rb') as file:
        # Read the RIFF chunk header
        chunk_id, chunk_size = read_chunk_header(file)
        if chunk_id != b'RIFF':
            raise ValueError("File is not a valid RIFF file")

        format_type = file.read(4).decode('utf-8')
        sf2_data['format'] = format_type

        while file.tell() < chunk_size + 8:  # 8 bytes for RIFF header
            sub_chunk_id, sub_chunk_size = read_chunk_header(file)
            if sub_chunk_id is None:
                break

            if sub_chunk_id == b'LIST':
                list_type, sub_chunks = read_list_chunk(file, sub_chunk_size)
                sf2_data['chunks'].append({'id': sub_chunk_id, 'type': list_type, 'sub_chunks': sub_chunks})
            else:
                chunk_data = file.read(sub_chunk_size)
                sf2_data['chunks'].append({'id': sub_chunk_id, 'data': chunk_data})

    return sf2_data

def write_sf2(file_path, sf2_data):
    with open(file_path, 'wb') as file:
        # Write the RIFF header
        riff_size = calculate_total_riff_size(sf2_data)
        riff_header = struct.pack('<4sI', b'RIFF', riff_size) + sf2_data['format'].encode('utf-8')
        file.write(riff_header)

        # Write each chunk
        for chunk in sf2_data['chunks']:
            if 'sub_chunks' in chunk:  # LIST type chunk
                list_size = calculate_list_size(chunk)
                list_header = struct.pack('<4sI', chunk['id'], list_size) + chunk['type'].encode('utf-8')
                file.write(list_header)

                for sub_chunk in chunk['sub_chunks']:
                    file.write(struct.pack('<4sI', sub_chunk, len(chunk['sub_chunks'][sub_chunk])))
                    file.write(chunk['sub_chunks'][sub_chunk])
            else:  # Regular chunk
                file.write(struct.pack('<4sI', chunk['id'], len(chunk['data'])))
                file.write(chunk['data'])

def calculate_total_riff_size(sf2_data):
    size = 4  # For format type (e.g., 'sfbk')
    for chunk in sf2_data['chunks']:
        size += 8  # 4 bytes for ID, 4 bytes for size
        if 'sub_chunks' in chunk:
            size += calculate_list_size(chunk)
        else:
            size += len(chunk['data'])
    return size

def calculate_list_size(list_chunk):
    size = 4  # For list type (e.g., 'pdta')
    for sub_chunk_id, sub_chunk_data in list_chunk['sub_chunks'].items():
        size += 8 + len(sub_chunk_data)
    return size


def describe_chunk(chunk):
    if isinstance(chunk, dict):
        # Chunk is a dictionary, likely containing sub-chunks
        return f"Sub-chunks: {list(chunk.keys())}"
    elif isinstance(chunk, bytes):
        # Chunk is raw binary data
        data_length = len(chunk)
        preview = chunk[:20]  # Show the first 20 bytes as a preview
        return f"Raw data (length {data_length} bytes): {preview}"
    else:
        return "Unknown chunk type"


def parse_shdr_chunk(chunk_data):
    sample_headers = []
    header_format = '20sIIIIIBbHH'  # Adjusted format string for the SampleHeader structure
    header_size = struct.calcsize(header_format)  # Calculate the size of one header

    for i in range(0, len(chunk_data) - header_size + 1, header_size):
        try:
            unpacked_data = struct.unpack_from(header_format, chunk_data, i)
        except struct.error:
            # Stop if there's not enough data left to read a full header
            break

        sample_header = {
            'name': unpacked_data[0].split(b'\x00', 1)[0].decode('utf-8', errors='ignore'),
            'start': unpacked_data[1],
            'end': unpacked_data[2],
            'startLoop': unpacked_data[3],
            'endLoop': unpacked_data[4],
            'sampleRate': unpacked_data[5],
            'originalPitch': unpacked_data[6],
            'pitchCorrection': unpacked_data[7],
            'link': unpacked_data[8],
            'type': unpacked_data[9],
        }
        sample_headers.append(sample_header)

    return sample_headers

def pack_shdr_chunk(sample_headers):
    packed_data = b''
    header_format = '20sIIIIIBbHH'

    for header in sample_headers:
        packed_data += struct.pack(header_format,
                                   header['name'].encode('utf-8'),
                                   header['start'],
                                   header['end'],
                                   header['startLoop'],
                                   header['endLoop'],
                                   header['sampleRate'],
                                   header['originalPitch'],
                                   header['pitchCorrection'],
                                   header['link'],
                                   header['type'],
        )
    return packed_data

def get_idx_shdr(shdr_data, name):
    for idx, sample_header in enumerate(shdr_data):
        if sample_header['name'] == name:
            return idx
    return None

def get_loops_from_file(loop_file_path):
    loop_dict = {}
    #filepath = os.path.join(preset_dir, "selected_loops.txt")

    with open(loop_file_path, 'r') as file:
        for line in file:
            parts = line.strip().split(',')
            if len(parts) >= 3:  # Ensure there are enough parts in the line
                filename = parts[0].split('/')[-1]
                start, stop = int(parts[1]), int(parts[2])
                loop_dict[filename] = (start, stop)
    return loop_dict

def get_shdr_data(sf2_data):
    pdta = sf2_data['chunks'][2]
    shdr = pdta['sub_chunks'][b'shdr']
    return parse_shdr_chunk(shdr)

# Open soundfont and show sample headers
#sf = read_sf2(soundfont_file)
#pdta = sf[b'RIFF']['sub_chunks']['LIST (pdta)']
#shdr = pdta[b'shdr']
#parsed_headers = parse_shdr_chunk(shdr)
#for header in parsed_headers:
#    print(header)
#
#shdr_data[0]['startLoop'] = 66666
#shdr_data[0]['endLoop'] = 66666

sf2_dir = "/home/equant/projects/audio/sf2"
soundfont_file = 'Casio MT-70.sf2'
soundfont_path = os.path.join(sf2_dir, soundfont_file)

sf2_data = read_sf2(soundfont_path)
shdr_data = get_shdr_data(sf2_data)
original_shrd_data = shdr_data.copy()

synth_dir = "/home/equant/projects/audio/casio2soundfont/recordings/Casio Casiotone MT-70"

for idx, sample in enumerate(shdr_data):
    print(f"Sample: {sample['name']}")
    if sample['name'] == 'EOS':
        continue
    preset = sample['name'][:-3]
    preset_dir = os.path.join(synth_dir, preset)
    loop_file_path = os.path.join(preset_dir, "selected_loops.txt")
    if not os.path.isfile(loop_file_path):
        shdr_data[idx]['startLoop'] = 0
        shdr_data[idx]['endLoop'] = 0
        print(f"No loop file found for {preset}")
        continue
    loop_dict = get_loops_from_file(loop_file_path)
    wavefile = sample['name'] + ".wav"
    sample_length = shdr_data[idx]['end'] - shdr_data[idx]['start']
    shdr_data[idx]['startLoop'] = sample['start'] + loop_dict[wavefile][0]
    shdr_data[idx]['endLoop'] = sample['start'] + loop_dict[wavefile][1]

new_shdr = pack_shdr_chunk(shdr_data)
sf2_data['chunks'][2]['sub_chunks'][b'shdr'] = new_shdr
new_sounndfont_path = os.path.join(sf2_dir, "modified.sf2")
write_sf2(new_sounndfont_path, sf2_data)

modified_sf2_data = read_sf2(new_sounndfont_path)
modified_shdr_data = get_shdr_data(modified_sf2_data)

print(original_shrd_data[-2])
print(shdr_data[-2])
print(modified_shdr_data[-2])

print(sf2_data['chunks'][2]['sub_chunks'][b'shdr'])
print(modified_sf2_data['chunks'][2]['sub_chunks'][b'shdr'])
