# BibleGateway-to-Obsidian

## ⚠️ Disclaimers

By default, the version is set to the [WEB Bible](https://worldenglish.bible/). You can change the version but **must honour the copyright standards** of different translations of the Bible (See for example [BibleGateway's overview](https://www.biblegateway.com/versions/)).

Using the script with some versions is **clearly breaking copyright**. The script is not intended for such usage.

For example, for the ESV from https://www.esv.org/resources/esv-global-study-bible/copyright-page/:

> "The ESV text may be quoted (in written, visual, or electronic form) up to and inclusive of five hundred (500) consecutive verses without express written permission of the publisher, provided that the verses quoted do not amount to more than one-half of any one book of the Bible or its equivalent measured in bytes and provided that the verses quoted do not account for twenty-five percent (25%) or more of the total text of the work in which they are quoted."

The NET translation, however has very generous copyright rules: https://netbible.com/copyright/. It appears to be permissible to use for personal study.

This is not affiliated to, or approved by, BibleGateway.com. In my understanding it fits into the [conditions of usage](https://support.biblegateway.com/hc/en-us/articles/360001398808-How-do-I-get-permission-to-use-or-reprint-Bible-content-from-Bible-Gateway-?), but I make no guarantee regarding the usage of the script, it is at your own discretion.

## About

This script is inspired by [jgclark's BibleGateway-to-Markdown](https://github.com/jgclark/BibleGateway-to-Markdown) and exports for use in [Obsidian](https://obsidian.md/). It accompanies a [Bible Study in Obsidian Kit](https://forum.obsidian.md/t/bible-study-in-obsidian-kit-including-the-bible-in-markdown/12503?u=selfire) that gets you hands-on with using Scripture in your personal notes.
This script is inspired by [jgclark's BibleGateway-to-Markdown](https://github.com/jgclark/BibleGateway-to-Markdown) and exports for use in [Obsidian](https://obsidian.md/). It accompanies a [Bible Study in Obsidian Kit](https://forum.obsidian.md/t/bible-study-in-obsidian-kit-including-the-bible-in-markdown/12503?u=selfire) that gets you hands-on with using Scripture in your personal notes.

What the script does is fetch the text from [Bible Gateway](https://www.biblegateway.com/) and save it as a formatted markdown file. Each chapter is saved as one file and navigation between files as well as a book-file is automatically created. All the chapter files of a book are saved in its numbered folder.

This script is intended to be as simple as possible to use, even if you have no idea about scripting. If you have any questions, please reach out to me either on GitHub or Discord (`selfire#3095`).

## Languages
You can find supported languages in the [locales](https://github.com/selfire1/BibleGateway-to-Obsidian/tree/main/locales) folder.

## Installation

Requirements:

- Python 3.9+
Requirements:

- Python 3.9+

## Usage

### 1. Run from this directory
### 1. Run from this directory

Open your terminal application, and navigate to this directory with commands like the following:
Open your terminal application, and navigate to this directory with commands like the following:

- `pwd` Show your current directory
- `ls` List all contents in the current directory
- `cd` Enter a subdirectory (e.g., `cd Desktop`)
- `cd ..` Brings you 'up' one directory

### 2. Run the script

Once you have navigated to the directory, run `python bg2obs.py`. A folder named like `The Bible (WEB)` with subfolders like `Genesis`, `Exodus` and so on will be created in the current folder.
Once you have navigated to the directory, run `python bg2obs.py`. A folder named like `The Bible (WEB)` with subfolders like `Genesis`, `Exodus` and so on will be created in the current folder.

Several options are available via command-line switches. Type `python bg2obs.py -h` at any time to display them.
Several options are available via command-line switches. Type `python bg2obs.py -h` at any time to display them.

#### Script option summary

| Option         | Description                                                                                                                                            |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `-v [VERSION]` | Specify the version of the Bible to download (default is WEB)                                                                                          |
| `-a`           | Create an alias in the YAML front matter with a more user-friendly chapter title (e.g., "Genesis 1") (default is Off)                                  |
| `-b`           | Set words of Jesus in bold (default is Off)                                                                                                            |
| `-c`           | Include _inline_ navigation for the [breadcrumbs](https://github.com/SkepticMystic/breadcrumbs) plugin (e.g. 'up', 'next','previous') (default is Off) |
| `-e`           | Include editorial headers (default is Off)                                                                                                             |
| `-i`           | Show progress information while the script is running (i.e. "verbose" mode) (default is Off)                                                           |
| `-l`           | Specify the locale that should be used to name the books of the Bible (default is English). See [supported locales](https://github.com/selfire1/BibleGateway-to-Obsidian/tree/main/locales).                                                             |
| `-s`           | If available, use shorter book abbreviations                                                                                                           |
| `-y`           | Include navigation for the breadcrumbs plugin in the _frontmatter_ (YAML) (default is Off)                                                             |
| `--abbr`       | Use medium-length abbreviations for filenames (booksAbbr.txt)                                                                                          |
| `--book`       | Limit download to a single book (use locale spelling or abbreviation)                                                                                  |
| `--chapter`    | Limit download to a single chapter (requires --book)                                                                                                   |
| `--footnotes`  | Include footnotes in the text and footer                                                                                                               |
| `--list-versions` | List available version abbreviations from BibleGateway                                                                                              |
| `-h`           | Display help                                                                                                                                           |

    
#### Example usage

| Command                         | Description                                                                                |
| ------------------------------- | ------------------------------------------------------------------------------------------ |
| `python bg2obs.py -i -v NET`      | Download a copy of the NET Bible with no other options.                                    |
| `python bg2obs.py -b`             | Download a copy of the WEB Bible (default) with Jesus' words in bold.                      |
| `python bg2obs.py -y`             | Download a copy of the WEB Bible (default) with breadcrumbs navigation in the frontmatter. |
| `python bg2obs.py -v NET -beacyi --footnotes` | Download a copy of the NET Bible with all options enabled.                                 |

### 3. Format the text in a text editor

Some cross references are sometimes still included, run `\<crossref intro.*crossref\>` to delete.

**There you go!** Now, just move the generated Bible folder into your Obsidian vault. You can use the provided Bible index file as an overview file.
**There you go!** Now, just move the generated Bible folder into your Obsidian vault. You can use the provided Bible index file as an overview file.

## Translations

This script downloads the [World English Bible](https://worldenglish.bible/) by default. If you want to download a different translation, specify the version using the `-v` command-line switch as documented above. The list of abbreviations is available on the [Bible Gateway](https://www.biblegateway.com) site under the version drop-down menu in the search bar. Make sure to honour copyright guidelines. The script has not been tested with all versions of the Bible available at Bible Gateway, though most of the more commonly-used ones should work.

A fork of the original repo supports Catholic translations: [mkudija/BibleGateway-to-Obsidian-Catholic](https://github.com/mkudija/BibleGateway-to-Obsidian-Catholic).

## Troubleshooting 🐛

Below are common issues when using the script. If this still doesn't solve your issue, there are some place to get help:

- The [Help and Support thread](https://forum.obsidian.md/t/bible-study-kit-in-obsidian-scripts-help-and-support/31069/2) for this script in the Obsidian Forums. (I am somewhat less active there, but plenty of folks are happy to help out!)
- Create an [issue](https://github.com/selfire1/BibleGateway-to-Obsidian/issues) on GitHub. This is my preferred way to keep track of what needs fixing.
- Also, feel free to [get in touch](https://joschua.io/about) and I will attempt to fix it!

### "Language not found: error
Make sure to download the whole repository. See [issue 44](https://github.com/selfire1/BibleGateway-to-Obsidian/issues/44) for more information.

## Contributing

Pull requests are welcome.
You can help me keep creating tools like this by [buying me a coffee](https://www.buymeacoffee.com/joschua). ☕️

<a href="https://www.buymeacoffee.com/joschua" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" height= "48" width="173"></a>

### Locales

You can contribute by translating this script into your language.

Copy the [locales/en](https://github.com/selfire1/BibleGateway-to-Obsidian/tree/main/locales/en) folder and rename it with the relevant language tag. Add the translations in a `books.txt`, `booksAbbr.txt`, `booksAbbrShort.txt` and `name.txt` files.
