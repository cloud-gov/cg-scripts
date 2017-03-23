package main

import (
	"bufio"
	"bytes"
	"fmt"
	"io/ioutil"
	"log"
	"net/http"
	"os/exec"
	"regexp"
	"sort"
	"strings"
	"sync"

	"gopkg.in/yaml.v2"
)

// parse and sort the buildpack manifest yaml
type dependencyDeprecationDate struct {
		Date    string
		Name    string
		Version string `yaml:"version_line"`
}

type dependencyDeprecationDates []dependencyDeprecationDate

func (slice dependencyDeprecationDates) Len() int {
	return len(slice)
}

func (slice dependencyDeprecationDates) Less(i, j int) bool {
	return slice[i].Date < slice[j].Date;
}

func (slice dependencyDeprecationDates) Swap(i, j int) {
	slice[i], slice[j] = slice[j], slice[i]
}

type buildpackManifest struct {
	DependencyDeprecationDates dependencyDeprecationDates `yaml:"dependency_deprecation_dates"`
}


func main() {
	var wg sync.WaitGroup

	// git a list of buildpacks the janky way
	out, err := exec.Command("cf", "buildpacks").Output()
	if err != nil {
		log.Fatal(err)
	}

	//parse out the name of the buildpack and the version
	r, _ := regexp.Compile(`^(.+?) .+(v\d+.*)\.zip$`)
	scanner := bufio.NewScanner(bytes.NewBuffer(out))
	for scanner.Scan() {
		buildpack := r.FindSubmatch(scanner.Bytes())
		wg.Add(1)

		go func() {
			defer wg.Done()

			if len(buildpack) == 0 {
				return
			}

			// grab the manifest from github
			repo := strings.Replace(string(buildpack[1]), "_", "-", -1)
			version := string(buildpack[2])
			resp, err := http.Get("https://raw.githubusercontent.com/cloudfoundry/" + repo + "/" + version + "/manifest.yml")
			if err != nil {
				log.Fatal(err)
			}

			defer resp.Body.Close()
			yamldata, err := ioutil.ReadAll(resp.Body)
			if err != nil {
				log.Fatal(err)
			}

			// parse the yaml
			manifest := buildpackManifest{}

			err = yaml.Unmarshal(yamldata, &manifest)
			if err != nil {
				log.Fatal(err)
			}

			// if we have info, print it sorted by date
			if len(manifest.DependencyDeprecationDates) == 0 {
				return
			}

			sort.Sort(manifest.DependencyDeprecationDates)

			fmt.Printf("%s %s\n", repo, version)
			for _, item := range manifest.DependencyDeprecationDates {
				fmt.Printf("\t%s - %s %s\n", item.Date, item.Name, item.Version)
			}

		}()

	}

	wg.Wait()
}

