#! /usr/bin/env python
"""
__author__ = Yao LI
__email__ = yao.li.binf@gmail.com
__date__ = 08/02/2018
"""
import numpy as np
import editdistance


#############################
#  Human Imprinted Regions  #
#############################
class ImprintedRegions:
    """
    Define the imprinted regions on human genome (EnSembl hg38).
    Save the data in a dictionary.
    """

    def __init__(self, filename):
        """
        :param filename: (string) path of the file stores the
                         information of certain imprinted regions.
        """
        self.regions = {}
        file = open(filename, "r")
        for line in file:
            line = line.strip().split("\t")
            self.regions[line[0]] = line[1:]
        file.close()

    def get_regions(self):
        """
        :return: (dictionary) key = gene names
        """
        return self.regions


##################
# Nanopore reads #
##################
class NanoporeReads:
    """
    Discover reads that are overlapped with human imprinted regions.
    From one sam file.
    """

    def __init__(self, samfile, chrom):
        """
        Open a sam file, extract data of reads
        mapped to the right chromosome on reference genome.
        :param samfile: (string) path of external sam file
        :param chrom: (string) chromosome number
        """
        self.samfile = samfile  # store filename as an attribute]
        try:
            if 1 <= int(chrom) <= 22:
                self.chrom = "chr" + chrom
        except ValueError:
            if chrom in ["XxYx"]:
                self.chrom = "chr" + chrom.lower()
            else:
                raise Exception("Invalid chromosome number.")

        file = open(self.samfile, "r")
        self.data = {}
        self.reads = {}
        self.overlap = {}
        for line in file:
            if line.startswith("@"):  # ignore headers
                pass
            else:
                line = line.split("\t")
                self.data[line[0]] = line[1:]
                # calculate the region of a READs mapped on to the reference genome
                start = int(line[3])
                seq = line[9]
                seq_len = len(seq)
                end = (start + seq_len)
                rname = line[2]
                if rname == self.chrom:  # some READs may map to other chromosomes
                    self.reads[line[0]] = (start, end, rname, seq)
        file.close()

    def get_data(self):
        """
        :return: (dictionary) all data from the sam file as a dictionary.
        """
        return self.data

    def get_reads(self):
        """
        :return: (dictionary) information of names,
                 start and end positions of reads.
        """
        return self.reads

    def get_sequence(self, read_name):
        """
        :param read_name: (string) Nanopore basecalling ID
        :return: (string) sequence of the given READs
        """
        return self.data[read_name][8]

    def search_reads(self, reads_names):
        """
        Search reads based on their given QNAMEs.
        :param reads_names: (string) Nanopore basecalling ID
        :return: boolean value
        """
        for qname in reads_names:
            try:
                self.data.get(qname)
            except ValueError:
                print("This READs does not exist.")
        return True

    def find_imprinted(self, regions, thrhld, save_file=False, file=None):
        """
        For a given sam file, find out if there is any READs in the file
        is located in human genetic imprinted regions.
        :param regions: (dictionary) positions of human imprinted regions on reference genome
        :param thrhld: (float) a number between 0 and 1. portion? does not matter
        :param save_file: (bool) if want to save the result to a txt file
        :param file: (string) path of the file to save results
        :return: (dictionary) key = imprinted reads ID
                            values: overlapped imprinted gene name
                            which end of the READs located in the imprinted region
                            positions of overlap segment refer to the original READs
                            positions of overlap segment refer to the reference genome
                            threshold been used
        """
        self.overlap = {}
        gene = {}; b = 0; s = 0; e = 0; n = 0; cnt = 0
        for j in regions:  # j = gene name
            c = 0
            start = int(regions[j][0])
            end = int(regions[j][1])
            r_range = range(start, end + 1)
            chrom = regions[j][2]  # chr is just a number(str)
            for i in self.reads:  # i = READs ID
                # make sam id and fast5 id the same format
                if i.find("_Basecall_1D_template"):
                    read_id = i.replace("_Basecall_1D_template", "")
                else:
                    read_id = i.replace("_Basecall_Alignment_template", "")

                pos1, pos2, rname, seq = self.reads[i]  # pos1 & pos2 are int
                if 0 <= thrhld <= 1:
                    min_coverage = thrhld * (pos2 - pos1)
                else:
                    print("t is a float between 0 and 1.")
                    return
                if chrom == rname.replace("chr", ""):
                    if pos1 in r_range and pos2 in r_range:
                        b += 1; cnt += 1
                        l = pos2 - pos1
                        # if both ends of the READs located in an imprinted region
                        if min_coverage <= l:
                            n += 1; c += 1
                            gene[j] = c
                            self.overlap[read_id] = [j, self.chrom, "both ends",
                                                     (1, l + 1),
                                                     (pos1, pos2),
                                                     thrhld, seq]
                    elif pos1 in r_range and pos2 not in r_range:
                        s += 1; cnt += 1
                        l1 = end - pos1  # overlapped length
                        if min_coverage <= l1:
                            n += 1; c += 1
                            gene[j] = c
                            self.overlap[read_id] = [j, self.chrom, "start pos",
                                                     (1, l1 + 1),
                                                     (end - l1, end),
                                                     thrhld, seq]
                    elif pos2 in r_range and pos1 not in r_range:
                        e += 1; cnt += 1
                        l2 = pos2 - start
                        if min_coverage <= l2:
                            n += 1; c += 1
                            gene[j] = c
                            self.overlap[read_id] = [j, self.chrom, "end pos",
                                                     (pos2 - pos1 - l2, pos2 - pos1),
                                                     (start, start + l2), thrhld, seq]
        # Save results into a txt file
        if save_file:
            file = open(file, "w")
            file.write(
                "Read_ID\t\tImprinted_Gene\t\tChromosome\t\tInfo\t\tPos_On_Read"
                "\t\tPos_On_Ref_Genome\t\tIR_Length_Threshold\n\n")
            for id in self.overlap:
                file.write("{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\n\n".format(id, self.overlap[id][0],
                                                                       self.overlap[id][1],
                                                                       self.overlap[id][2],
                                                                       self.overlap[id][3],
                                                                       self.overlap[id][4],
                                                                       self.overlap[id][5],
                                                                       self.overlap[id][6]))
            file.write("\n{} reads pass the threshold.\n".format(n))
            for name in gene:
                file.write("{} in gene {}\n".format(gene[name], name))
            file.write(
                "\nTotal {} reads have both ends located in "
                "an imprinted region.\n{} reads start position"
                " mapped to imprinted region.\n{} reads end position"
                " mapped to imprinted region.\n".format(b, s, e))
            file.write("\nTotal {} chr19 reads have overlap "
                       "with chr19 imprinted regions.\n".format(cnt))
            file.close()

    def get_imprinted_reads(self):
        """
        :return: (list) imprinted Nanopore reads IDs
        """
        return self.overlap

    def search_imprinted_read(self, ID):
        return self.overlap[ID]

    def get_matrix(self):
        """
        Calculate the minimum edit distance between two reads.
        :return: (numpy narray) pairwise distance matrix
        """
        if not self.overlap == []:
            dist_matrix = np.zeros((len(self.overlap), len(self.overlap)))
            a = 0
            for i in self.overlap:
                seq1 = self.get_sequence(i)
                b = 0
                for j in self.overlap:
                    seq2 = self.get_sequence(j)
                    dist_matrix[a, b] = editdistance.eval(seq1, seq2)
                    b += 1
                a += 1
            return dist_matrix
        else:
            print("The list of imprinted reads is empty.")

    def get_read_len(self, read):
        """for id in self.reads:
                read_len = self.get_read_len(self.reads[key])"""
        return len(read[3])


################
class NR:
    def __init__(self, id, seq, chr, poses):
        self.id = id
        self.raw_signal = None
        self.sequence = seq
        self.chr = chr
        self.poses = poses
        self.overlap_region = None
        self.gene = ""
        self.overlap_fastq = ""
        self.overlap_pos = (0, 0)
        self.haplotype = ""
        self.snps = []


def load_Sam(samfile, chrom):
    data = []
    file = open(samfile, "r")
    for line in file:
        if line.startswith("@"):  # ignore headers
            pass
        else:
            line = line.split("\t")
            rname = line[2]
            if rname == chrom:  # some READs may map to other chromosomes
                start = int(line[3])
                seq = line[9]
                seq_len = len(seq)
                end = (start + seq_len)
                nr = NR(line[0], seq, rname, (start, end))
                data.append(nr)
    file.close()
    return data

###############