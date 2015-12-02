<?php

/*
  TODO:
  * Language/locale.
  * Pagination.
  * Media.
  * FIX EDUCATION LEVELS: need to regularize ranges & representations somehow.
 */

require_once(dirname(__DIR__) . '/config.php');

setlocale(LC_ALL, 'en_US');
bindtextdomain("CCOERSearch", "../locale");
textdomain("CCOERSearch");

$MAX_PAGES = 1000;
$COUNT_PER_PAGE = 20;

function next_page ($page_num) {
    global $MAX_PAGES;
    return max(0, min($page_num++, $MAX_PAGES));
}

function previous_page ($page_num) {
    global $MAX_PAGES;
    return min($MAX_PAGES - 1, max($page_num--, 0));
}

function search_from ($page) {
    global $COUNT_PER_PAGE, $MAX_PAGES;
    $page = max(0, min($page, $MAX_PAGES));
    return $page * $COUNT_PER_PAGE;
}

function should_next_page ($page, $more_results) {
    global $COUNT_PER_PAGE;
    return $more_results && ($page < $COUNT_PER_PAGE);
}

function should_previous_page ($page) {
    return $page > 0;
}

function print_pagination ($args, $page, $more_results) {
    if (should_previous_page($page)) {
        $merged_args = $args;
        $merged_args['page'] = previous_page($page);
        echo '<a href="index.php?'. http_build_query($merged_args)
            . '">'. _('Previous page') . '</a>';
    } else {
        echo _('Previous page');
    }
    echo '&nbsp;&nbsp;&mdash;&nbsp;&nbsp;';
    if (should_next_page($page, $more_results)) {
        $merged_args = $args;
        $merged_args['page'] = next_page($page);
        echo '<a href="index.php?'. http_build_query($merged_args)
            . '">'. _('Next page') . '</a>';
    } else {
        echo _('Next page');
   }
}

// NEED TOTAL OVERHAUL
$education_levels = [
    0 => 'Any',
    10 => 'Elementary School',
    11 => 'Upper Elementary',
    12 => 'Middle School',
    13 => 'High School',
    14 => 'Higher Education',
    16 => 'Undergraduate (Lower Division)',
    17 => 'Undergraduate (Upper Division)'
];

$license_names = [
    0 => '',
    1 => 'by-nc-sa',
    2 => 'by-nc',
    3 => 'by-nc-nd',
    4 => 'by',
    5 => 'by-sa',
    6 => 'by-nd'
];

// Licenses by id number (public domain is separate)
// LICENSE -> [TRUE, FALSE] for match of license_modules

$license_elements = [
    0 => [[], []],
    1 => [[], ['by', 'nc', 'sa'], ['nd']],
    2 => [['by', 'nc'], ['nd', 'sa']],
    3 => [['by', 'nc', 'nd'], ['sa']],
    4 => [['by'], ['nc', 'nd', 'sa']],
    5 => [['by', 'sa'], ['nc', 'nd']],
    6 => [['by', 'nd'], ['nc', 'sa']]
];

// Licenses by groups of affordances (adaptation, commercial use)
// LICENSE -> [TRUE, FALSE] for match of license_modules
// Desired affordances: c = commercial, a = adapt
// If not desired you may still get them, but if desired they must be present
// These are the elements we *cannot* have under these conditions

$affordance_elements = [
    '' => [[], []],
    'c' => [[], ['nc']],
    'a' => [[], ['nd']],
    'ca' => [[], ['nc', 'nd']],
];

$media = [
    0 => 'Any',
    1 => 'Text',
    2 => 'Audio',
    3 => 'Image',
    4 => 'Video',
    5 => 'Software',
    6 => 'Course'
];

function print_education_levels ($selected_id) {
    global $education_levels;
    foreach ($education_levels as $id => $name) {
        echo '<option ';
        if ($id == $selected_id) {
            echo 'selected ';
        }
        echo 'value="'. $id . '">' . $name . '</option>';
    }
}

function termClauses($terms_string) {
    /*$terms = preg_split('/[\s]+/', $terms_string);
    $term_clauses = array_map(function($term) {
        return ['match' => ['description' => $term]];
    },
                              $terms);
    return $term_clauses;*/
    return ['match' => ['description' => [
                'query' => strtolower($terms_string),
                'operator' => 'and'
                ]]];
}

function queryString ($terms_string) {
    $terms = preg_split('/[\s]+/', $terms_string);
    return join(' AND ', $terms);
}

function public_domain_query() {
    return ['term' =>['license_category' => 'publicdomain']];
}

function cc_license_query($license_number) {
    global $license_names;
    return ['term' =>['license_name' => $license_names[$license_number]]];
}

function license_query_from_number($license_number) {
    if ($license_number <= 0 || $license_number >= 8) {
        $matches = False;
    } else if ($license_number < 7) {
        $matches = cc_license_query($license_number);
    } else {
        $matches = public_domain_query();
    }
    return $matches;
}

function level_query_from_number($level_number) {
    global $education_levels;
    if (($level_number > 0)
        && array_key_exists($level_number, $education_levels)) {
        $matches = [
            'term' => [
                'levels' => $education_levels[$level_number]
                ]
            ];
    } else {
        $matches = [];
    }
    return $matches;
}

if (isset($_GET['query'])) {
    //FIXME: constrain to maximum term count, apply boolean & grouping logic
    $must_clauses = [];
    $must_clauses[] = termClauses($_GET['query']);
    $level_number = intval($_GET['level']);
    $level_clauses = level_query_from_number($level_number);
    $license_number = intval($_GET['license']);
    $license_clauses = license_query_from_number($license_number);
    $page = intval($_GET['page']);

    if ($level_clauses) {
        $must_clauses[] = $level_clauses;
    }
    if ($license_clauses) {
        $must_clauses[] = $license_clauses;
    }

    $bool_queries = ['must' => $term_clauses];

    $client = Elasticsearch\ClientBuilder::create()
                  ->setHosts(\Config::$elastic_lr_hosts)
                  ->build();
    $params = [
        'index' => \Config::$elastic_lr_index,
        'body' => [
            'query' => [
                'bool' =>  [
                    'must' => $must_clauses
                    ]
                ]
            ]
        ];
    error_log(print_r($params, true));
    $search_results = $client->search($params);
    error_log(print_r($search_results, true));
}
?>
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <!-- The above 3 meta tags *must* come first in the heaD; any other head content must come *after* these tags -->
    <title>CC OER Search Demo</title>

    <!-- Bootstrap -->
    <!-- Latest compiled and minified CSS -->
    <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.5/css/bootstrap.min.css" integrity="sha512-dTfge/zgoMYpP7QbHy4gWMEGsbsdZeCXz7irItjcC3sPUFtf0kuFbDz/ixG7ArTxmDjLXDmezHubeNikyKGVyQ==" crossorigin="anonymous">

    <!-- HTML5 shim and Respond.js for IE8 support of HTML5 elements and media queries -->
    <!-- WARNING: Respond.js doesn't work if you view the page via file:// -->
    <!--[if lt IE 9]>
      <script src="https://oss.maxcdn.com/html5shiv/3.7.2/html5shiv.min.js"></script>
      <script src="https://oss.maxcdn.com/respond/1.4.2/respond.min.js"></script>
    <![endif]-->

    <link rel="stylesheet" href="css/style.css">
  </head>
  <body>
        <div class="navbar navbar-inverse navbar-fixed-top" role="navigation">
      <div class="container">
        <div class="navbar-header">
          <button type="button" class="navbar-toggle collapsed"
                  data-toggle="collapse" data-target=".navbar-collapse">
            <span class="sr-only">Toggle navigation</span>
            <span class="icon-bar"></span>
            <span class="icon-bar"></span>
            <span class="icon-bar"></span>
          </button>
          <a class="navbar-brand" href="/"><?php
            echo _('Creative Commons OER Search'); ?></a>
        </div>
        <div class="collapse navbar-collapse">
        </div><!--/.nav-collapse -->
      </div>
    </div>

    <div class="container">
      <div class="main">
        <h2><?php echo _('Search'); ?></h2>
        <form action="index.php" class="form" role="form">
          <div class="form-group">
            <label for="query"><?php echo _('Terms'); ?></label>
            <input type="text" class="form-control" id="query" name="query"
                   placeholder="monkeys"
                   value="<?php
                          //FIXME: save cleaned string earlier and use that here
                          if (isset($_GET['query'])) {
                              echo $_GET['query'];
                          }
                          ?>"></input>
          </div>
          <div class="form-group"">
            <label for="license"><?php echo _('License'); ?></label>
            <select class="form-control" id="license" name="license">
              <option <?php if ($_GET['license'] == 4) echo 'selected'; ?>
                value="4"><?php echo _('Creative Commons Attribution'); ?></option>
              <option <?php if ($_GET['license'] == 5) echo 'selected'; ?>
                 value="5"><?php echo _('Creative Commons Attribution-ShareAlike'); ?></option>
              <option <?php if ($_GET['license'] == 2) echo 'selected'; ?>
                 value="2"><?php echo _('Creative Commons Attribution-NonCommercial'); ?></option>
              <option <?php if ($_GET['license'] == 1) echo 'selected'; ?>
                 value="1"><?php echo _('Creative Commons Attribution-NonCommercial-ShareAlike'); ?></option>
              <option <?php if ($_GET['license'] == 6) echo 'selected'; ?>
                 value="6"><?php echo _('Creative Commons Attribution-NoDerivs'); ?></option>
              <option <?php if ($_GET['license'] == 3) echo 'selected'; ?>
                 value="3"><?php echo _('Creative Commons Attribution-NonCommercial-NoDerivs'); ?></option>
              <option <?php if ($_GET['license'] == 7) echo 'selected'; ?>
                 value="7"><?php echo _('Public Domain (CC0/PDM)'); ?></option>
              <option <?php if ($_GET['license'] == 0) echo 'selected'; ?>
                value="0"><?php echo _('Any'); ?></option>
            </select>
          </div>
          <div class="form-group"">
            <label for="level"><?php echo _('Education Level'); ?></label>
            <select class="form-control" id="level" name="level">
              <?php print_education_levels($level_number); ?>
            </select>
          </div>
          <button type="submit" class="btn btn-default">Search</button>
        </form>
        <?php
        if (isset($search_results)) {
            $result_count = count($search_results['hits']['hits']);
            if (isset($search_results['hits']['hits'])
                && $result_count > 0) {
              echo '<h2>' . _('Results') . '</h2>';
              echo '<table class="table table-striped"><thead>';
              echo '<tr><th>' . _('Title')
                   . '</th><th>' . _('License') . '</th><th>'
                   . _('Link') . '</th></tr>';
              echo '</thead><tbody>';
              foreach ($search_results['hits']['hits'] as $key => $item) {
                  $sr = $item['_source'];
                  echo '<tr><td>' . $sr['title'] . '</td>'
                     . '<td>' . $sr['license_name'] . '</td>'
                     .'<td><a href="' . $sr['resource_locator']
                     . '">' . $sr['resource_locator']
                     . '</a></td></tr>';
              }
              echo '</tbody></table><p>';
              print_pagination($_GET, $page, $result_count == $COUNT_PER_PAGE);
              echo '</p><p><br><i>' . _('Results from <a href="http://learningregistry.org/">The Learning Registry</a>.') . '</i></p>';
          } else {
              echo '<br><div class="alert alert-info" role="alert">' . _('That did not match anything') . '</div>';
          }
        }
        ?>
      </div>
    </div>
    <!-- jQuery (necessary for Bootstrap's JavaScript plugins) -->
    <script src="https://ajax.googleapis.com/ajax/libs/jquery/1.11.3/jquery.min.js"></script>
    <!-- Include all compiled plugins (below), or include individual files as needed -->
    <!-- Latest compiled and minified JavaScript -->
<script src="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.5/js/bootstrap.min.js" integrity="sha512-K1qjQ+NcF2TYO/eI3M6v8EiNYZfA95pQumfvcVrTHtwQVDG+aHRqLi/ETn2uB+1JqwYqVG3LIvdm9lj6imS/pQ==" crossorigin="anonymous"></script>
  </body>
</html>
